import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import importlib
import json
from pathlib import Path
import sys
import threading

import pytest


@dataclass
class Response:
    content: str
    tool_calls: list = field(default_factory=list)
    finish_reason: str = None
    raw_response: object = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@pytest.fixture
def api(monkeypatch):
    module = importlib.import_module('reviewer_analysis.revision_v2.planning_codex')
    monkeypatch.setattr(module, '_response_types', lambda: (Response, ToolCall))
    return module


class Transport:
    model = 'gpt-5.5'
    public_config = {'requested_model': 'gpt-5.5', 'reasoning_effort': 'medium'}

    def __init__(self, answer='["raw array"]', failure=False, gate=None):
        self.answer, self.failure, self.gate = answer, failure, gate
        self.prompts = []

    def invoke_at(self, prompt, trace_dir):
        self.prompts.append(prompt)
        if self.gate:
            self.gate[0].set()
            self.gate[1].wait(timeout=5)
        if self.failure:
            call = Path(trace_dir) / 'failed'
            call.mkdir(parents=True)
            (call / 'events.jsonl').write_text(json.dumps({'type': 'turn.completed',
                'usage': {'input_tokens': 8, 'output_tokens': 2}}) + '\n')
            raise RuntimeError('private secret must not be journaled')
        return self.answer, {'input_tokens': 10, 'output_tokens': 3, 'cli_call_id': 'test'}, None


def adapter(api, tmp_path, max_calls=3, **transport_kwargs):
    ledger = api.CallLedger(max_calls, journal=tmp_path / 'ledger.json')
    transport = Transport(**transport_kwargs)
    return api.CodexAdapter(tmp_path / 'traces', ledger, transport=transport), ledger, transport


def test_roles_share_cap_preserve_raw_output_and_reserve_final(api, tmp_path):
    main, ledger, transport = adapter(api, tmp_path)
    memory = main.for_role('memory')
    assert memory.transport is main.transport
    assert main.chat([{'role': 'user', 'content': 'return array'}]).content == '["raw array"]'
    memory.chat([{'role': 'user', 'content': 'update'}])
    with pytest.raises(api.BudgetExceeded):
        main.chat([{'role': 'user', 'content': 'excess'}])
    assert len(transport.prompts) == 2
    assert ledger.exhausted
    ledger.begin_final()
    main.for_role('final').chat([{'role': 'user', 'content': 'report'}])
    with pytest.raises(api.BudgetExceeded):
        main.chat([{'role': 'user', 'content': 'excess final'}])
    snapshot = ledger.snapshot()
    assert snapshot['calls_used'] == 3
    assert snapshot['known_usage'] == {'input_tokens': 30, 'output_tokens': 9}
    assert snapshot['unknown_usage_calls'] == 0
    assert [r['role'] for r in snapshot['calls']] == ['main', 'memory', 'final']
    assert snapshot['token_policy'] == 'measured_only'
    assert json.loads((tmp_path / 'ledger.json').read_text()) == snapshot


def test_atomic_cap_and_final_phase_wait_for_inflight(api, tmp_path):
    entered, release = threading.Event(), threading.Event()
    main, ledger, transport = adapter(api, tmp_path, max_calls=2, gate=(entered, release))
    with ThreadPoolExecutor(max_workers=8) as pool:
        future = pool.submit(main.chat, [{'role': 'user', 'content': 'hold'}])
        assert entered.wait(timeout=2)
        with pytest.raises(RuntimeError, match='inflight'):
            ledger.begin_final()
        attempts = [pool.submit(main.chat, [{'role': 'user', 'content': 'race'}]) for _ in range(6)]
        for attempt in attempts:
            with pytest.raises(api.BudgetExceeded):
                attempt.result()
        release.set()
        future.result()
    assert len(transport.prompts) == 1
    assert ledger.snapshot()['inflight'] == 0
    ledger.begin_final()


def test_failed_calls_count_and_recover_usage_without_error_secrets(api, tmp_path):
    main, ledger, transport = adapter(api, tmp_path, max_calls=2, failure=True)
    with pytest.raises(RuntimeError):
        main.chat([{'role': 'user', 'content': 'fail'}])
    snapshot = ledger.snapshot()
    assert ledger.exhausted
    assert snapshot['known_usage'] == {'input_tokens': 8, 'output_tokens': 2}
    assert snapshot['calls'][0]['status'] == 'failed'
    assert snapshot['inflight'] == 0
    assert 'private secret' not in (tmp_path / 'ledger.json').read_text()


def test_missing_failed_usage_is_unknown(api, tmp_path):
    class Broken(Transport):
        def invoke_at(self, *args):
            raise RuntimeError('failed before trace')
    ledger = api.CallLedger(2)
    main = api.CodexAdapter(tmp_path, ledger, transport=Broken())
    with pytest.raises(RuntimeError):
        main.chat([{'role': 'user', 'content': 'fail'}])
    assert ledger.snapshot()['unknown_usage_calls'] == 1
    assert ledger.snapshot()['calls_used'] == 1


def test_tools_are_serialized_and_returned_to_native_executor(api, tmp_path):
    main, ledger, transport = adapter(api, tmp_path, answer=json.dumps({
        'content': 'search', 'tool_calls': [{'id': 's1', 'name': 'search', 'arguments': {'query': 'x'}}]}))
    tools = [{'type': 'function', 'function': {'name': 'search', 'parameters': {'type': 'object'}}}]
    response = main.chat([{'role': 'tool', 'tool_call_id': 'old', 'content': 'result'}], tools)
    assert response.tool_calls == [ToolCall('s1', 'search', {'query': 'x'})]
    assert response.content == 'search'
    assert 'tool_call_id' in transport.prompts[0] and 'parameters' in transport.prompts[0]
    assert ledger.snapshot()['calls'][0]['output_sha256']


@pytest.mark.parametrize('answer', ['[]', '{"content":"x","tool_calls":[{"id":"a","name":"unknown","arguments":{}}]}',
    '{"content":"x","tool_calls":[{"id":"a","name":"search","arguments":"{}"}]}'])
def test_invalid_tool_protocol_is_counted_without_retry(api, tmp_path, answer):
    main, ledger, transport = adapter(api, tmp_path, answer=answer)
    with pytest.raises(ValueError):
        main.chat([{'role': 'user', 'content': 'x'}], [{'name': 'search'}])
    assert ledger.snapshot()['calls_used'] == 1
    assert ledger.snapshot()['known_usage']['input_tokens'] == 10
    assert ledger.snapshot()['calls'][0]['status'] == 'failed'


def test_async_and_stream_use_same_ledger(api, tmp_path):
    main, ledger, _ = adapter(api, tmp_path, max_calls=4)
    assert asyncio.run(main.achat([{'role': 'user', 'content': 'x'}])).content == '["raw array"]'
    assert len(list(main.stream_chat([{'role': 'user', 'content': 'x'}]))) == 1
    async def consume():
        return [r async for r in main.astream_chat([{'role': 'user', 'content': 'x'}])]
    assert len(asyncio.run(consume())) == 1
    assert ledger.exhausted


def test_transport_reuses_historical_invoker_with_retry_config(api, tmp_path):
    script = tmp_path / 'cli.py'
    script.write_text('''import json,sys
from pathlib import Path
if '--version' in sys.argv:
 print('fake-codex'); sys.exit(0)
args=sys.argv[1:]
Path(__file__).with_suffix('.args.json').write_text(json.dumps(args))
sys.stdin.read()
answer='["untouched"]'
Path(args[args.index('-o')+1]).write_text(answer)
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':answer}}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':4,'output_tokens':2}}))
''')
    transport = api.PlanningCodexClient(tmp_path / 'transport', executable=[sys.executable, str(script)])
    ledger = api.CallLedger(2)
    result = api.CodexAdapter(tmp_path / 'calls', ledger, transport=transport).chat([{'role': 'user', 'content': 'x'}])
    assert result.content == '["untouched"]'
    args = json.loads(script.with_suffix('.args.json').read_text())
    assert 'model_providers.openai.request_max_retries=0' in args
    assert 'model_providers.openai.stream_max_retries=0' in args
    assert args[args.index('--model') + 1] == 'gpt-5.5'
    assert transport.public_config['model_snapshot_attested'] is False
    assert ledger.snapshot()['known_usage']['input_tokens'] == 4
