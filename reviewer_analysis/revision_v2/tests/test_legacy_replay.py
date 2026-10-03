from pathlib import Path
import pytest

SOURCE=Path(__file__).parents[1]/'reproducibility/historical_q4_metric_20261003/eval_scpqa.py'

class Fake:
    def __init__(self,fail=False):self.prompts=[];self.fail=fail
    def chat_legacy(self,prompt):
        self.prompts.append(prompt)
        if self.fail:raise RuntimeError('transport failed')
        response='A, B' if len(self.prompts)==1 else '[["A", "R"], ["B", "R"], ["invented", "S"]]'
        return response,{'input_tokens':1,'output_tokens':1},None


def test_original_replay_retains_truncation_many_to_one_and_unchecked_ids():
    from reviewer_analysis.revision_v2.legacy_replay import replay_record
    client=Fake();report='x'*8000+'AFTER_TRUNCATION'
    r=replay_record(SOURCE,{'id':61,'question':'Which?','report':report},'R, S',client)
    assert 'AFTER_TRUNCATION' not in client.prompts[0]
    assert len(r['matches'])==3
    assert r['components']['answer_precision']==1.5
    assert r['components']['answer_recall']==1
    assert r['components']['answer_f1']==pytest.approx(1.2)
    assert r['components']['legacy_composite']==pytest.approx(1.128)
    assert r['original_result']['per_question'][0]['graph_f1']==1.128
    assert r['audit']['unknown_predicted']==['invented']
    assert r['audit']['many_predictions_to_one_reference'] is True


def test_legacy_silent_extraction_failure_cannot_be_reported_as_success():
    from reviewer_analysis.revision_v2.legacy_replay import replay_record
    with pytest.raises(RuntimeError,match='transport'):
        replay_record(SOURCE,{'id':61,'question':'Which?','report':'A'},'R',Fake(True))
