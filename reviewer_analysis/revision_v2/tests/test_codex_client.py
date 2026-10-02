import json
import os
from pathlib import Path
import sys

import pytest

from reviewer_analysis.revision_v2.common import read_jsonl


def fake_cli(tmp_path, mode='ok'):
    path = tmp_path / 'fake_codex.py'
    path.write_text('''import json,sys,time
from pathlib import Path
if '--version' in sys.argv:
 print('codex-cli test'); sys.exit(0)
args=sys.argv[1:]
prompt=sys.stdin.read()
Path(__file__).with_suffix('.request.json').write_text(json.dumps({'args':args,'prompt':prompt}))
mode=''' + repr(mode) + '''
print(json.dumps({'type':'thread.started','thread_id':'test'}),flush=True)
if mode=='timeout': time.sleep(30)
if mode=='failed':
 print(json.dumps({'type':'turn.failed','error':{'message':'synthetic failure'}})); sys.exit(1)
answer='{"value": "closed book"}'
Path(args[args.index('-o')+1]).write_text(answer)
if mode=='tool': print(json.dumps({'type':'item.completed','item':{'type':'command_execution','command':'not actually executed'}}))
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':answer}}))
if mode!='no_usage': print(json.dumps({'type':'turn.completed','usage':{'input_tokens':16384 if mode=='numbers' else 10,'output_tokens':5}}))
''')
    return [sys.executable, str(path)]


def test_exact_model_and_private_prompt_trace(tmp_path):
    from reviewer_analysis.revision_v2.codex_client import CodexClient
    executable = fake_cli(tmp_path)
    client = CodexClient(tmp_path / 'calls', executable=executable)
    raw, usage, model = client.chat('Use only supplied evidence.', {'claim':'A -> B'})
    request = json.loads(Path(executable[1]).with_suffix('.request.json').read_text())
    assert request['args'][request['args'].index('--model')+1] == 'gpt-5.5'
    assert '--ignore-user-config' in request['args']
    assert 'web_search="disabled"' in request['args']
    assert json.loads(raw)['value'] == 'closed book'
    assert usage['input_tokens'] == 10
    assert model is None
    assert len(list((tmp_path/'calls').glob('*/events.jsonl'))) == 1
    assert client.public_config['hard_token_cap'] is None


@pytest.mark.parametrize('mode', ['tool', 'no_usage', 'failed'])
def test_incomplete_or_tool_using_runs_rejected_and_retained(tmp_path, mode):
    from reviewer_analysis.revision_v2.codex_client import CodexClient
    client = CodexClient(tmp_path/'calls', executable=fake_cli(tmp_path, mode))
    with pytest.raises(RuntimeError): client.chat('Return JSON', {})
    logs = list((tmp_path/'calls').glob('*/events.jsonl'))
    assert len(logs) == 1 and 'thread.started' in logs[0].read_text()


def test_timeout_retains_events(tmp_path):
    from reviewer_analysis.revision_v2.codex_client import CodexClient
    client = CodexClient(tmp_path/'calls', executable=fake_cli(tmp_path, 'timeout'), timeout=.2)
    with pytest.raises(RuntimeError): client.chat('Return JSON', {})
    exits = list((tmp_path/'calls').glob('*/exit.json'))
    assert json.loads(exits[0].read_text())['timed_out'] is True
    assert 'thread.started' in (exits[0].parent/'events.jsonl').read_text()


def test_token_setting_does_not_corrupt_numeric_usage(tmp_path, monkeypatch):
    from reviewer_analysis.revision_v2.codex_client import CodexClient
    monkeypatch.setenv('REVIEW_JUDGE_MAX_TOKENS', '16384')
    client = CodexClient(tmp_path/'calls', executable=fake_cli(tmp_path, 'numbers'))
    _, usage, _ = client.chat('Return JSON', {})
    assert usage['input_tokens'] == 16384
    events=read_jsonl(next((tmp_path/'calls').glob('*/events.jsonl')))
    assert events[-1]['usage']['input_tokens'] == 16384


def test_model_cannot_overwrite_label_identity_or_assessor_provenance():
    from reviewer_analysis.revision_v2.judging import validate_judgment
    result=validate_judgment({'truth_status':'unresolved','citation_status':'unavailable',
        'quotes':[], 'reason':'No source', 'fact_id':'other', 'assessor_type':'human',
        'raw_judgment':'overwritten', 'api_calls':0, 'returned_model':'fake'}, {})
    assert not set(result) & {'fact_id','assessor_type','raw_judgment','api_calls','returned_model'}


def test_invalid_extraction_preserves_raw_response_and_is_not_rerun(tmp_path, monkeypatch):
    from reviewer_analysis.revision_v2 import evaluation
    class Fake:
        public_config = {'model':'fake'}
        calls = 0
        def chat(self, *_):
            self.calls += 1
            return '{"nodes":[{"id":"n1","name":"A","node_type":"company","quote":"invented"}],"edges":[]}', {'input_tokens':12}, 'fake'
    client = Fake()
    monkeypatch.setattr(evaluation, 'make_client', lambda _:client)
    records = [{'method':'test','run_id':'one','query_id':'Q61','quadrant':'Q4','question':'q','report':'actual report'}]
    first = evaluation.extract_reports(records, tmp_path, execute=True)
    second = evaluation.extract_reports(records, tmp_path, execute=True)
    assert first['n_failed'] == 1 and second['requests_made'] == 0
    assert client.calls == 1
    item = json.loads(next((tmp_path/'items').glob('*.json')).read_text())
    assert item['raw_response'].startswith('{"nodes"')
    assert item['usage']['input_tokens'] == 12
    assert item['error_kind'] == 'content_validation'
    assert read_jsonl(tmp_path/'results.jsonl') == []
