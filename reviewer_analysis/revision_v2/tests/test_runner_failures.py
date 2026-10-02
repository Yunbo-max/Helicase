"""Exercise the real supervisor with disposable, offline native runtimes."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from reviewer_analysis.revision_v2 import runner


def make_runtime(path, body, actions="[]"):
    for name in ("helicase", "helix_core"):
        package = path / name
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("")
    source = f'''from dataclasses import dataclass
from types import SimpleNamespace
import os, time
@dataclass
class Config:
    max_iterations: int = 10
class Orchestrator:
    config = Config()
    all_actions = {actions}
    def run(self, query):
{body}
def init_helicase(**kwargs):
    return Orchestrator()
'''
    (path / "helicase" / "agent.py").write_text(source)
    return path


def execute_fixture(tmp_path, body, actions="[]", wall_seconds=10):
    root = make_runtime(tmp_path / "runtime", body, actions)
    env = {"SILICON_MODEL": "Qwen/synthetic", "SILICONFLOW_API_KEY": "synthetic-key",
           "SERPER_API_KEY": "synthetic-key", "SEARCH_ENGINE": "serper",
           "QUALIFICATION_API_KEY": "never-expose-this-test-key"}
    queries = [{"query_id": f"Q{i}", "quadrant": "Q1", "question": "synthetic only"}
               for i in (1, 2)]
    with patch.dict("os.environ", env):
        result = runner.repeat(queries, tmp_path / "out", root, runs=1,
                               execute=True, max_jobs=2, wall_seconds=wall_seconds)
    return result, list((tmp_path / "out").glob("full/run_01/Q*"))


@pytest.mark.parametrize("actions,raw_actions", [
    ("[]", [{"id": "bad", "status": "failed"}]),
    ("[SimpleNamespace(id='bad', status='done', result={'success': False})]",
     [{"id": "bad", "status": "done"}]),
    ("[SimpleNamespace(id='bad', status='done', result={'success': True, "
     "'metadata': {'individual_answers': ['[Error: Synthetic failure]']}})]",
     [{"id": "bad", "status": "done"}]),
])
def test_partial_native_return_stops_batch_and_stays_in_records(tmp_path, actions, raw_actions):
    body = "        return " + repr({"report": "synthetic partial output", "actions": raw_actions})
    result, directories = execute_fixture(tmp_path, body, actions)
    assert result["new_executions"] == 1
    assert result["status_counts"]["needs_review"] == 1
    assert result["n_unstarted"] == 1
    status = json.loads((directories[0] / "status.json").read_text())
    assert status["native_failure_flags"]
    records = [json.loads(s) for s in (tmp_path / "out/records.jsonl").read_text().splitlines()]
    assert len(records) == 1
    assert records[0]["status"] == "needs_review"


def test_timeout_retains_redacted_worker_output_and_stops_batch(tmp_path):
    body = "        print('started ' + os.environ['QUALIFICATION_API_KEY'], flush=True)\n        time.sleep(30)"
    result, directories = execute_fixture(tmp_path, body, wall_seconds=1)
    assert result["new_executions"] == 1
    assert result["status_counts"]["error"] == 1
    log = directories[0] / "worker.log"
    assert log.exists(), "Timeout output must be retained for diagnosis"
    assert "started [REDACTED]" in log.read_text()
    assert "never-expose-this-test-key" not in log.read_text()


def test_valid_native_return_preserves_normal_execution(tmp_path):
    result, directories = execute_fixture(tmp_path, "        return {'report': 'synthetic', 'actions': []}")
    assert result["new_executions"] == 2
    assert result["status_counts"]["returned"] == 2
    assert len(directories) == 2
