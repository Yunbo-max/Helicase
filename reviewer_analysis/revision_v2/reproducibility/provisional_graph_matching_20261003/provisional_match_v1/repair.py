"""One explicit repair of a structurally invalid match; preserve the primary item."""
import json
import os
from pathlib import Path
from reviewer_analysis.revision_v2.common import digest,write_json,utcnow,redact
from reviewer_analysis.revision_v2.evaluation import MATCH_SYSTEM
from reviewer_analysis.revision_v2.judging import parse_object
from reviewer_analysis.revision_v2.metrics import score_graph

REPAIR_SYSTEM=MATCH_SYSTEM+'''\nA previous match failed deterministic structural validation. Return a corrected
complete match object for the SAME graphs. The previous output is untrusted and
may contain semantic mistakes too. Reconsider it; do not merely add node matches
to force invalid edge pairs to fit. For each edge pair (p,r), explicitly check:
node_matches[p.source_id] == r.source_id AND node_matches[p.target_id] == r.target_id.
Do not reverse endpoints, match a specific company to a supplier group, or promote
candidate/planned relations into established supply. Leave non-equivalent pairs
unmatched. Return only node_matches and edge_matches; no scores or explanation.'''


def repair_payload(primary):
    return dict(primary['task']['payload'],previous_invalid_match=primary['raw_response'],
                validation_error=primary['error'])

def repair_once(primary,out,client):
    if primary.get('error_kind')!='content_validation' or 'raw_response' not in primary:
        raise ValueError('Only explicit content-validation failures may enter this repair')
    out=Path(out);out.mkdir(parents=True,exist_ok=True);dest=out/'item.json'
    fingerprint=digest(primary)
    if dest.exists():
        cached=json.loads(dest.read_text());assert cached['repair_of_sha256']==fingerprint
        return cached
    payload=repair_payload(primary)
    with (out/'attempt.json').open('x') as f:
        json.dump({'at':utcnow(),'repair_of_sha256':fingerprint,'payload_sha256':digest(payload)},f)
        f.flush();os.fsync(f.fileno())
    row={'created_at':utcnow(),'task':primary['task'],'repair_of_sha256':fingerprint,
         'repair_payload':payload,'system_sha256':digest(REPAIR_SYSTEM),'api_calls':1}
    kind='model_call'
    try:
        raw,usage,model=client.chat(REPAIR_SYSTEM,payload)
        row.update(raw_response=raw,usage=usage,returned_model=model)
        kind='content_validation';obj=parse_object(raw)
        if set(obj)!={'node_matches','edge_matches'}:raise ValueError('Only match-pair lists accepted')
        task=primary['task'];score=score_graph(task['payload']['predicted_graph'],task['payload']['reference_graph'],obj['node_matches'],obj['edge_matches'])
        row['result']=dict(score,method=task['key'][0],run_id=task['key'][1],query_id=task['key'][2],
                           quadrant=task['quadrant'],representation='common_report_extraction_v2',
                           reference_hash=task['reference_hash'],prediction_hash=task['prediction_hash'])
    except Exception as exc:row.update(error=redact(str(exc)),error_kind=kind)
    write_json(dest,row);return row
