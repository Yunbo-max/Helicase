"""Read only explicitly selected SCQA members. Never extract arbitrary ZIP paths."""
from __future__ import annotations
import json
import math
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from .common import digest, file_hash, new_directory, qid, utcnow, write_json, write_jsonl

FILES = {
    'scpqa_qwen3.jsonl':'Helicase', 'scpqa_react.jsonl':'ReAct',
    'scpqa_tot.jsonl':'ToT', 'scpqa_claude_opus.jsonl':'Claude',
    'scpqa_qwen3_235b.jsonl':'Qwen3-235B', 'scpqa_deepseek_v3.jsonl':'DeepSeek',
    'scpqa_glm5.jsonl':'GLM',
}
EVALS = {'eval_report.json','eval_react.json','eval_tot.json','eval_claude_opus.json',
         'eval_qwen3_235b.json','eval_deepseek_v3.json','eval_glm5.json'}


def records_dict(value):
    if value is None: return {}
    if isinstance(value, dict): return value
    if isinstance(value, list):
        out={}
        for row in value:
            ident=str(row['id'])
            if ident in out: raise ValueError('Duplicate native graph record ID')
            out[ident]=row
        return out
    raise ValueError('Graph records must be a dict or list')


def native_facts(record):
    kg = record.get('knowledge_graph') or {}
    nodes, edges = records_dict(kg.get('nodes')), records_dict(kg.get('edges'))
    refs = {str(k):v for k,v in (record.get('ref2url') or {}).items()}
    result=[]
    record_hash = record.get('record_hash') or digest(record)
    for kind, objects in [('node',nodes),('edge',edges)]:
        for key, raw in objects.items():
            u=raw.get('uncertainty')
            if isinstance(u,bool) or (u is not None and not isinstance(u,(int,float))):
                raise ValueError(f'Non-numeric uncertainty in {record["query_id"]}:{key}')
            if u is not None and not math.isfinite(u): raise ValueError('Non-finite uncertainty')
            ref_ids=raw.get('evidence_refs' if kind=='edge' else 'sources') or []
            if not isinstance(ref_ids,list): raise ValueError('Expected a list of reference identifiers')
            urls=[]; missing=[]
            for rid in ref_ids:
                ref=refs.get(str(rid)); url=ref.get('url') if isinstance(ref,dict) else ref
                if isinstance(url,str) and url.startswith(('https://','http://')):
                    if url not in urls: urls.append(url)
                else: missing.append(str(rid))
            if kind=='edge':
                h=nodes.get(str(raw.get('source_id')),{}); t=nodes.get(str(raw.get('target_id')),{})
                claim=f'{h.get("name",raw.get("source_id"))} --{raw.get("relation_type","UNKNOWN")}--> {t.get("name",raw.get("target_id"))}'
                valid=bool(h and t and raw.get('relation_type'))
            else:
                claim=f'Entity: {raw.get("name",key)}. Type: {raw.get("node_type","unspecified") }.'
                valid=bool(raw.get('name'))
            fields={k:record[k] for k in ('query_id','quadrant','question','method','run_id')}
            # Scope is explicit metadata only; never inferred from an arbitrary path.
            props=raw.get('properties') or {}
            scope={k:props.get(k) for k in ('valid_from','valid_to','market','facility','product','geography')}
            fact_id=digest({'record':record_hash, 'kind':kind,'id':key})[:24]
            result.append(dict(fields, fact_id=fact_id, original_id=str(key), fact_type=kind,
                 score_semantics='stored_edge_score' if kind=='edge' else 'node_score_evaluated_on_identity_only',
                 claim=claim, scope=scope, confidence=None if u is None else 1.0-u,
                 stored_uncertainty=u, confidence_in_range=u is None or 0<=u<=1,
                 structural_validity=valid, citation_urls=urls, reference_ids=list(map(str,ref_ids)),
                 unresolved_reference_ids=missing))
    return result


def normalize_record(raw, method, run_id='archived_single_run'):
    ident=qid(raw.get('query_id',raw.get('id')))
    question=raw.get('question',raw.get('query',''))
    quadrant=raw.get('quadrant')
    if not question or quadrant not in ('Q1','Q2','Q3','Q4'): raise ValueError('Missing question/quadrant')
    return {'query_id':ident,'quadrant':quadrant,'question':question,'method':method,
            'run_id':run_id,'record_hash':digest(raw),'status':raw.get('status','unknown'),
            'report':raw.get('report',''),'knowledge_graph':raw.get('knowledge_graph',{}),
            'ref2url':raw.get('ref2url',{}),'uncertainty':raw.get('uncertainty',{}),
            'actions':raw.get('actions',[]),'elapsed_seconds':raw.get('elapsed_seconds'),
            'iterations':raw.get('iterations'),'model':raw.get('model')}


def invalid_metrics(obj, path=''):
    issues=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            here=f'{path}/{k}'
            if isinstance(v,(int,float)) and not isinstance(v,bool) and any(s in k.lower() for s in ('precision','recall','f1','accuracy','calibration_error')):
                if not math.isfinite(v) or not 0<=v<=1: issues.append({'path':here,'value':v})
            issues.extend(invalid_metrics(v,here))
    elif isinstance(obj,list):
        for i,v in enumerate(obj): issues.extend(invalid_metrics(v,f'{path}/{i}'))
    return issues


def prepare(archive, out, methods=None):
    out=Path(out)
    allowed=FILES if methods is None else {k:v for k,v in FILES.items() if v in methods}
    if not allowed: raise ValueError('No recognised methods requested')
    all_records=[]; questions={}; member_hashes={}; selected=set(); problems=[]
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            path=PurePosixPath(info.filename)
            if path.is_absolute() or '..' in path.parts or '__MACOSX' in path.parts: continue
            if any('iran' in p.lower() for p in path.parts): continue
            name=path.name
            if name not in allowed and name not in EVALS: continue
            if name in selected: raise ValueError(f'Ambiguous duplicate member {name}')
            selected.add(name)
            if info.file_size > 300_000_000: raise ValueError('Archive member too large')
            body=z.read(info); member_hashes[info.filename]=digest(body)
            if name in EVALS:
                problems.extend({'file':name,**r} for r in invalid_metrics(json.loads(body)))
                continue
            seen=set()
            for line in body.decode('utf-8-sig').splitlines():
                if not line.strip(): continue
                raw=json.loads(line); num=int(qid(raw.get('id'))[1:])
                if not 1<=num<=80: continue  # SCQA-80 only, never claim held-out status.
                r=normalize_record(raw,allowed[name])
                if r['query_id'] in seen: raise ValueError(f'Duplicate query in {name}: {r["query_id"]}')
                seen.add(r['query_id']); all_records.append(r)
                q={k:r[k] for k in ('query_id','quadrant','question')}
                if q['query_id'] in questions and questions[q['query_id']]!=q:
                    raise ValueError(f'Question text/quadrant disagreement: {q["query_id"]}')
                questions[q['query_id']]=q
    if not all_records: raise ValueError('No allowlisted SCQA records found')
    facts=[f for r in all_records for f in native_facts(r)]
    q4=[f for f in facts if f['quadrant']=='Q4' and f['method']=='Helicase' and f['fact_type']=='edge']
    audit={'suite_version':'2.0.0','created_at':utcnow(),'archive_sha256':file_hash(archive),
           'member_sha256':member_hashes,'record_counts':dict(Counter(r['method'] for r in all_records)),
           'invalid_archived_metrics':problems,
           'empty_native_graphs':[{'method':r['method'],'query_id':r['query_id']} for r in all_records if not (r['knowledge_graph'] or {}).get('edges')],
           'invalid_fact_scores':[f['fact_id'] for f in facts if not f['confidence_in_range']],
           'helicase_q4_edges':{'total':len(q4),'has_reference_id':sum(bool(f['reference_ids']) for f in q4),
                                'has_resolved_url':sum(bool(f['citation_urls']) for f in q4)},
           'limits':['No historical evaluator recovered. No gold graphs reconstructed from summaries.',
                     'Node diagnostics concern identity/type, not correctness of every node attribute.',
                     'Missing labels, time scope and citation entailment are not inferred.']}
    new_directory(out)
    write_jsonl(out/'records.jsonl',all_records)
    write_jsonl(out/'questions.jsonl',sorted(questions.values(),key=lambda x:int(x['query_id'][1:])))
    write_jsonl(out/'facts.jsonl',facts)
    sources={}
    for r in all_records:
        for v in r['ref2url'].values():
            url=v.get('url') if isinstance(v,dict) else v
            if isinstance(url,str) and url.startswith(('https://','http://')):
                sources.setdefault(url,{'url':url, 'source_id':digest(url)[:24]})
    write_jsonl(out/'source_urls.jsonl',sources.values())
    write_json(out/'audit.json',audit)
    return audit
