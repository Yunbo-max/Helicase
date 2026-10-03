"""Resume untouched primary tasks; explicitly repair only validation failures."""
import fcntl
import json
import os
from pathlib import Path
import sys

OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parents[3]))
from reviewer_analysis.revision_v2.common import digest,read_jsonl,write_json,utcnow
from reviewer_analysis.revision_v2.codex_client import CodexClient
from reviewer_analysis.revision_v2.evaluation import match_graphs
from repair import repair_once

os.environ.update(REVIEW_JUDGE_BACKEND='codex',REVIEW_JUDGE_MODEL='gpt-5.5',REVIEW_CODEX_TIMEOUT='600')
with (OUT/'run.lock').open('w') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    protocol=json.loads((OUT/'protocol.json').read_text())
    repair_policy=json.loads((OUT/'repair_protocol.json').read_text())
    assert digest((OUT/'repair.py').read_bytes())==repair_policy['source_sha256']
    assert digest((OUT/'protocol.json').read_bytes())==repair_policy['original_protocol_sha256']
    pred=Path(protocol['prediction_path']);ref=OUT/'references_provisional.jsonl'
    while True:
        assert digest(pred.read_bytes())==protocol['prediction_sha256']
        assert digest(ref.read_bytes())==protocol['reference_sha256']
        files=sorted((OUT/'matches/items').glob('*.json'))
        assert len(files)==len(list((OUT/'matches/calls').glob('*/request.json')))
        assert len(files)<=140
        repaired=0
        for f in files:
            row=json.loads(f.read_text())
            if 'error' not in row:continue
            if row.get('error_kind')!='content_validation':raise RuntimeError('Transport failure requires separate diagnosis')
            dest=OUT/'repairs'/f.stem
            if not (dest/'item.json').exists():
                assert len(list((OUT/'repairs').glob('*/attempt.json')))<repair_policy['max_repair_cli_calls']
            result=repair_once(row,dest,CodexClient(dest/'calls'))
            if 'error' in result:raise RuntimeError('Repair failed; preserve its output and stop')
            repaired+=1
        state={'at':utcnow(),'status':'complete_provisional' if len(files)==140 else 'running_provisional_matching',
               'completed':len(files),'total':140,'primary_failures_repaired':repaired,
               'primary_cli_calls':len(files),'repair_cli_calls':len(list((OUT/'repairs').glob('*/attempt.json'))),
               'reference_author_confirmed':False}
        write_json(OUT/'progress.json',state);print(json.dumps(state),flush=True)
        if len(files)==140:break
        result=match_graphs(read_jsonl(pred),read_jsonl(ref),OUT/'matches',max_calls=140-len(files),execute=True)
        print(json.dumps(result),flush=True)
