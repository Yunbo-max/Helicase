import importlib.util
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from reviewer_analysis.revision_v2.tests.test_codex_client import fake_cli


def client_class():
    path=Path(__file__).parent/'tertiary_runtime_terra/codex_client_terra.py'
    assert path.exists(), 'Secondary model transport not implemented'
    spec=importlib.util.spec_from_file_location('secondary_client_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.CodexClient


def test_secondary_uses_exact_distinct_model_and_preserves_payload(tmp_path,monkeypatch):
    monkeypatch.setenv('REVIEW_JUDGE_MODEL','gpt-5.6-terra')
    executable=fake_cli(tmp_path)
    client=client_class()(tmp_path/'calls',executable=executable)
    payload={'question':'q','claim':'A supplies B','sources':[{'text':'A supplies B.'}]}
    raw,usage,returned=client.chat('SAME SYSTEM',payload)
    captured=json.loads(Path(executable[1]).with_suffix('.request.json').read_text())
    assert captured['args'][captured['args'].index('--model')+1]=='gpt-5.6-terra'
    assert captured['prompt'].endswith(json.dumps(payload,ensure_ascii=False))
    assert client.public_config['requested_model']=='gpt-5.6-terra'
    assert returned is None and usage['input_tokens']==10


def test_secondary_refuses_primary_model(tmp_path,monkeypatch):
    monkeypatch.setenv('REVIEW_JUDGE_MODEL','gpt-5.5')
    with pytest.raises(ValueError):client_class()(tmp_path/'calls',executable=fake_cli(tmp_path))


@pytest.mark.parametrize('mode',['tool','no_usage','failed'])
def test_secondary_rejects_incomplete_or_tool_using_calls(tmp_path,monkeypatch,mode):
    monkeypatch.setenv('REVIEW_JUDGE_MODEL','gpt-5.6-terra')
    client=client_class()(tmp_path/'calls',executable=fake_cli(tmp_path,mode))
    with pytest.raises(RuntimeError):client.chat('SAME SYSTEM',{})
    assert len(list((tmp_path/'calls').glob('*/events.jsonl')))==1


def runner_module():
    path=Path(__file__).parent/'tertiary_runtime_terra/run_tertiary.py'
    assert path.exists(), 'Secondary replay runner not implemented'
    sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location('secondary_runner_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_no_sources_never_calls_model(tmp_path):
    module=runner_module()
    class Client:
        def chat(self,*args):raise AssertionError('No source must not call model')
    row=module.evaluate_one({'fact_id':'x','citation_urls':[]},{'sources':[]},tmp_path,Client())
    assert row['truth_status']=='unresolved' and row['api_calls']==0


def test_failure_retained_without_silent_retry(tmp_path):
    module=runner_module()
    class Client:
        calls=0
        def chat(self,*args):
            self.calls+=1;raise RuntimeError('Synthetic network failure')
    client=Client();fact={'fact_id':'x','citation_urls':['https://example.com']}
    payload={'sources':[{'source_id':'s','text':'A supplies B.'}]}
    first=module.evaluate_one(fact,payload,tmp_path,client)
    second=module.evaluate_one(fact,payload,tmp_path,client)
    assert first==second and client.calls==1
    assert first['error_kind']=='model_call' and first['fact_id']=='x'


def test_interrupted_attempt_requires_inspection(tmp_path):
    module=runner_module()
    class Client:
        calls=0
        def chat(self,*args):
            self.calls+=1;raise KeyboardInterrupt()
    client=Client();fact={'fact_id':'x','citation_urls':['https://example.com']}
    payload={'sources':[{'source_id':'s','text':'A supplies B.'}]}
    with pytest.raises(KeyboardInterrupt):module.evaluate_one(fact,payload,tmp_path,client)
    with pytest.raises(FileExistsError):module.evaluate_one(fact,payload,tmp_path,client)
    assert client.calls==1
