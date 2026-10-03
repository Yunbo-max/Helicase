"""Convert original prose references into unconfirmed, quote-grounded review drafts."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from reviewer_analysis.revision_v2.codex_client import CodexClient
from reviewer_analysis.revision_v2.common import digest,read_jsonl,write_json,write_jsonl,utcnow,redact
from reviewer_analysis.revision_v2.evaluation import EXTRACT_SYSTEM,validate_extraction
from reviewer_analysis.revision_v2.judging import parse_object

OUT=Path(__file__).resolve().parent
PRIVATE=OUT.parent
SYSTEM=EXTRACT_SYSTEM+'''\nThe report is an EXISTING prose reference answer being converted into an UNCONFIRMED
review draft. Do not treat the prose as verified world truth. Preserve explicit
negation, cancelled/planned agreements, uncertainty, dates, product variants and
geographic qualifiers in relation semantics and quotations. Do not replace
assembly/testing with chip fabrication, capability with actual supply, or a
general supplier relationship with a specific product's physical material flow.
Represent only claims actually stated in the report. Source URLs alone do not
establish additional facts. Never use the question premise as evidence. Use
contiguous verbatim quotation spans, never ellipses or punctuation substitutions.
Return only nodes and edges. Do not invent author approval, scope completion,
reference versions, judgments of prediction graphs, or numeric scores.'''


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def evaluate(packet,out,client):
    out=Path(out);qid=packet['query_id'];target=out/'items'/(qid+'.json')
    payload={'question':packet['question'],'report':packet['existing_text_answer']}
    if target.exists():
        row=json.loads(target.read_text())
        assert row['query_id']==qid and row['input_sha256']==digest(payload)
        return row
    marker=out/'attempts'/(qid+'.json');marker.parent.mkdir(parents=True,exist_ok=True)
    with marker.open('x') as fp:
        json.dump({'at':utcnow(),'query_id':qid,'input_sha256':digest(payload)},fp);fp.flush();os.fsync(fp.fileno())
    row={'query_id':qid,'created_at':utcnow(),'input_sha256':digest(payload),'payload':payload,'api_calls':1}
    kind='model_call'
    try:
        raw,usage,model=client.chat(SYSTEM,payload)
        row.update(raw_response=raw,usage=usage,returned_model=model)
        kind='content_validation';graph=validate_extraction(parse_object(raw),payload['report'])
        result=dict(packet,status='draft_from_original_text_requires_author_review',draft_reference_graph=graph,
                    reference_version=None,author_completeness_confirmation=None,adjudicator=None,adjudication_date=None,
                    draft_provenance={'input_sha256':digest(payload),'model_requested':'gpt-5.5',
                                      'graph_verified_as_world_truth':False,'original_text_only':True})
        row['result']=result
    except Exception as exc:row.update(error=redact(str(exc)),error_kind=kind)
    write_json(target,row);return row


def initialize():
    os.environ.update(REVIEW_JUDGE_MODEL='gpt-5.5',REVIEW_CODEX_TIMEOUT='600')
    packets=read_jsonl(PRIVATE/'reference_author_review.jsonl')
    source=ROOT/'benchmark/gt_q4.jsonl';original={f"Q{r['id']}":r for r in read_jsonl(source)}
    assert len(packets)==len(original)==20 and {r['query_id'] for r in packets}=={f'Q{i}' for i in range(61,81)}
    for row in packets:
        old=original[row['query_id']]
        assert row['existing_text_answer']==old['answer'] and row['existing_source_urls']==old['sources']
        assert row['author_completeness_confirmation'] is None and row['draft_reference_graph'] is None
        assert row['provenance']['sha256']==sha(source)
    client=CodexClient(OUT/'calls')
    paths=[source,PRIVATE/'reference_author_review.jsonl',
           PRIVATE/'gpt55_q4_batch_v1/assembled/common_graphs_with_repairs.jsonl',
           Path(__file__),ROOT/'reviewer_analysis/revision_v2/evaluation.py',ROOT/'reviewer_analysis/revision_v2/codex_client.py']
    manifest={'created_for':'Original reference prose -> unconfirmed review graph; no prediction extraction or matching',
              'client':client.public_config,'system_sha256':digest(SYSTEM),'packet_sha256':digest(packets),
              'files_sha256':{str(p):sha(p) for p in paths},'max_outer_calls':20,
              'repair_policy':'Stop on errors; no automatic retry. Exact source quotation and graph integrity required.',
              'authorization':'User said found it, start; preparation of reviewable draft, not author approval of graph truth.',
              'approval_gate':'All20drafts need explicit author completeness and scope confirmation before formal reference-based scoring.'}
    dest=OUT/'manifest.json'
    if dest.exists():assert json.loads(dest.read_text())==manifest,'Frozen draft inputs changed'
    else:write_json(dest,manifest)
    return packets,client


def run(limit):
    packets,client=initialize();calls=0
    for p in packets:
        target=OUT/'items'/(p['query_id']+'.json')
        if not target.exists():
            if calls>=limit:break
            calls+=1
        row=evaluate(p,OUT,client)
        print(json.dumps({'query_id':p['query_id'],'status':'failed' if 'error'in row else 'drafted','new_calls':calls}),flush=True)
        if 'error'in row:break
    items=[json.loads(p.read_text()) for p in sorted((OUT/'items').glob('*.json'))]
    drafts=[r['result'] for r in items if 'result'in r]
    write_jsonl(OUT/'draft_reference_graphs.jsonl',drafts)
    write_json(OUT/'progress.json',{'at':utcnow(),'n_drafts':len(drafts),'n_errors':sum('error'in r for r in items),
               'n_not_started':20-len(items),'new_cli_invocations':calls,'author_confirmed':0,'formal_match_started':False})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--max-calls',type=int,default=2);args=parser.parse_args()
    if not 1<=args.max_calls<=20:raise ValueError('Call cap must be1..20')
    with (OUT/'run.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(args.max_calls)
