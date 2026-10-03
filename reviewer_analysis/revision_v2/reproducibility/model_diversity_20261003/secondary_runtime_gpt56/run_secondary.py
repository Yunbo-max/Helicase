"""Frozen GPT-5.6-Sol secondary judge; exactly replay primary evidence payloads."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT))
from reviewer_analysis.revision_v2 import judging
from reviewer_analysis.revision_v2.common import digest,read_jsonl,write_json,write_jsonl,utcnow,redact
from codex_client_gpt56 import CodexClient

RUNTIME=Path(__file__).resolve().parent
REMAIN=RUNTIME.parent
PRIVATE=REMAIN.parent
SAMPLE=REMAIN/'secondary_sample'
OUT=REMAIN/'secondary_judge_gpt56_v1'
ASSESSOR='gpt-5.6-sol-codex-secondary-v1'


def evaluate_one(fact,payload,out,client):
    out=Path(out);target=out/'items'/(fact['fact_id']+'.json')
    if target.exists():return json.loads(target.read_text())
    row={'fact_id':fact['fact_id'],'assessor':ASSESSOR,'assessor_type':'llm','created_at':utcnow(),
         'input_sha256':digest(payload),'evidence_payload':payload,
         'n_cited_urls':len(fact.get('citation_urls',[])),'n_sources_shown':len(payload['sources']),
         'evidence_status_not_world_truth':True}
    if not payload['sources'] or not fact.get('structural_validity',True):
        row.update(truth_status='unresolved',citation_status='unavailable',quotes=[],
                   validation_status='no_usable_evidence_or_invalid_structure',api_calls=0)
    else:
        marker=out/'attempts'/target.name;marker.parent.mkdir(parents=True,exist_ok=True)
        with marker.open('x') as fp:
            json.dump({'at':utcnow(),'fact_id':fact['fact_id'],'input_sha256':digest(payload)},fp)
            fp.flush();os.fsync(fp.fileno())
        kind='model_call';row['api_calls']=1
        try:
            raw,usage,model=client.chat(judging.SYSTEM,payload)
            row.update(raw_judgment=raw,usage=usage,returned_model=model)
            kind='content_validation'
            row.update(judging.validate_judgment(judging.parse_object(raw),
                       {s['source_id']:s['text'] for s in payload['sources']}))
        except Exception as exc:row.update(error=redact(str(exc)),error_kind=kind)
    write_json(target,row)
    return row


def initialize():
    os.environ.update(REVIEW_JUDGE_MODEL='gpt-5.6-sol',REVIEW_CODEX_TIMEOUT='600')
    facts=read_jsonl(SAMPLE/'facts.jsonl');payload_rows=read_jsonl(SAMPLE/'evidence_payloads.jsonl')
    selection=json.loads((SAMPLE/'selection.json').read_text())
    ids=[f['fact_id'] for f in facts]
    assert ids==selection['selected_ids']==[r['fact_id'] for r in payload_rows]
    assert len(ids)==len(set(ids))==200
    assert hashlib.sha256((SAMPLE/'evidence_payloads.jsonl').read_bytes()).hexdigest()==selection['evidence_payloads_sha256']
    config=selection['primary_configuration']
    assert digest(judging.SYSTEM)==config['system_prompt_sha256']
    primary_root=PRIVATE/'gpt55_q4_batch_v1'
    pages=read_jsonl(primary_root/'pages/pages_screened_v1.jsonl');by_url={r['url']:r for r in pages}
    assert digest(pages)==config['pages_sha256']
    primary={r['fact_id']:r for r in read_jsonl(SAMPLE/'primary_labels.jsonl')}
    originals={r['fact_id']:r for path in sorted(primary_root.glob('judge/shard_*/items/*.json'))
               for r in [json.loads(path.read_text())]}
    payloads={r['fact_id']:r['evidence_payload'] for r in payload_rows}
    for fact,record in zip(facts,payload_rows):
        key=fact['fact_id'];payload=record['evidence_payload'];sources=[]
        for url in fact.get('citation_urls',[]):
            page=by_url[url]
            if page.get('status')=='ok' and page.get('text'):
                limit=config['chars_per_source']
                sources.append({'source_id':page['source_id'],'url':url,'captured_at':page.get('captured_at'),
                                'basis':page.get('basis','unspecified'),'text':page['text'][:limit],
                                'truncated':len(page['text'])>limit})
            if len(sources)>=config['max_sources']:break
        assert payload==judging.build_claim_payload(fact,sources)==originals[key]['evidence_payload']
        assert digest(payload)==record['input_sha256']==primary[key]['input_sha256']
        assert primary[key]=={k:v for k,v in originals[key].items() if k not in ('evidence_payload','raw_judgment')}
    client=CodexClient(OUT/'calls')
    pilot_ids=[f['fact_id'] for f in facts if payloads[f['fact_id']]['sources'] and f.get('structural_validity',True)][:2]
    model_cache=json.loads((REMAIN/'cli_model_catalog.json').read_text())
    assert any(m.get('slug')=='gpt-5.6-sol' and m.get('visibility')=='list' for m in model_cache)
    source_paths=[Path(judging.__file__),Path(judging.__file__).with_name('common.py'),
                  RUNTIME/'codex_client_gpt56.py',Path(__file__)]
    protocol={'client':client.public_config,'source_commit':'6a212e446111283c23de6baf6dcbcb9f370ba580',
              'sample_files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                    (SAMPLE/'facts.jsonl',SAMPLE/'primary_labels.jsonl',SAMPLE/'evidence_payloads.jsonl',SAMPLE/'selection.json')},
              'source_files_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
              'system_sha256':digest(judging.SYSTEM),'primary_configuration':config,
              'sample_size':200,'max_new_outer_calls':sum(bool(payloads[f['fact_id']]['sources']) and f.get('structural_validity',True) for f in facts),'pilot_ids':pilot_ids,'workers':2,
              'model_qualification':'Explicit distinct model ID accepted through CLI; no server model snapshot attestation.',
              'authorization':'User explicitly authorized another model such asGPT4o orGPT6 for the already frozen secondary sample.',
              'statistics':'Three-class confusion and per-primary-stratum agreement; show all200 and both-model-called subset separately; calibration delta on common binary facts only, query-cluster2000bootstrap; no population simple-random-sample claim.',
              'repairs':'Same strict quote validation as primary; invalid decisive quotes become unresolved. Invocation errors stop; no silent outer retry.'}
    OUT.mkdir(parents=True,exist_ok=True);dest=OUT/'protocol.json'
    if dest.exists():assert json.loads(dest.read_text())==protocol,'Frozen secondary protocol changed'
    else:write_json(dest,protocol)
    return facts,payloads,client,protocol


def progress(name,**values):
    row={'at':utcnow(),'stage':name,**values};write_json(OUT/'progress'/(name+'.json'),row)
    print(json.dumps(row),flush=True)


def verify_pilot(protocol):
    audit=[]
    for fid in protocol['pilot_ids']:
        row=json.loads((OUT/'items'/(fid+'.json')).read_text())
        assert 'error' not in row and row['api_calls']==1 and row['assessor']==ASSESSOR
        trace=OUT/'calls'/row['usage']['cli_call_id']
        request=json.loads((trace/'request.json').read_text())
        assert request['config']==protocol['client']
        assert request['argv'][request['argv'].index('--model')+1]=='gpt-5.6-sol'
        assert row['input_sha256']==digest(row['evidence_payload'])
        audit.append({'fact_id':fid,'input_sha256':row['input_sha256'],'call_id':row['usage']['cli_call_id'],
                      'validation_status':row['validation_status']})
    write_json(OUT/'pilot_audit.json',{'status':'passed','checked':audit,'gate':'Format, provenance, model request and exact input equality only; not labels or score values.'})


def run(stage,worker,facts,payloads,client,protocol):
    if stage=='pilot':assigned=[f for f in facts if f['fact_id'] in protocol['pilot_ids']]
    else:
        assert json.loads((OUT/'pilot_audit.json').read_text())['status']=='passed'
        assigned=facts[worker::2]
    name=stage+str(worker)
    for fact in assigned:
        if (OUT/'MODEL_STOP').exists():
            progress(name,status='blocked');return
        row=evaluate_one(fact,payloads[fact['fact_id']],OUT,client)
        if 'error' in row:
            write_json(OUT/'stop_detail.json',{'fact_id':fact['fact_id'],'error_kind':row['error_kind'],'error':row['error']})
            (OUT/'MODEL_STOP').touch();progress(name,status='blocked',fact_id=fact['fact_id']);return
        count=sum((OUT/'items'/(f['fact_id']+'.json')).exists() for f in assigned)
        progress(name,status='running',processed=count,total=len(assigned))
    if stage=='pilot':verify_pilot(protocol)
    progress(name,status='complete',processed=len(assigned),total=len(assigned))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['init','pilot','run']);parser.add_argument('--worker',type=int,choices=[0,1],default=0)
    args=parser.parse_args();facts,payloads,client,protocol=initialize()
    if args.stage=='init':print(json.dumps({'sample_size':len(facts),'model':client.model,'pilot_ids':protocol['pilot_ids']}))
    else:
        with (OUT/(args.stage+str(args.worker)+'.lock')).open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            run(args.stage,args.worker,facts,payloads,client,protocol)
