import importlib.util
from pathlib import Path
import sys
import pytest


def test_rerun_cannot_erase_author_decisions(tmp_path,monkeypatch):
    path=Path(__file__).with_name('finalize_drafts.py');sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location('draft_finalize_test',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    review=tmp_path/'review_packet';review.mkdir()
    decision=review/'author_decisions.jsonl';decision.write_text('{"author_completeness_confirmation":true}\n')
    monkeypatch.setattr(mod,'REVIEW',review)
    with pytest.raises(FileExistsError):mod.main()
    assert decision.read_text()=='{"author_completeness_confirmation":true}\n'
