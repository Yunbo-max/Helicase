import pytest


def graph():
    return {'nodes':[{'id':'a','name':'A','node_type':'company','quote':'A'},
                     {'id':'b','name':'B','node_type':'company','quote':'B'}],
            'edges':[{'id':'e','source_id':'a','target_id':'b','relation_type':'supplies',
                      'evidence_status':'reported','quote':'A sells to B'}]}


def test_targeted_patch_changes_only_quote():
    from reviewer_analysis.revision_v2.quote_patch import apply_quote_patches
    original=graph()
    repaired,changes=apply_quote_patches(original,'A supplies B.',[
        {'kind':'edges','id':'e','quote':'A supplies B.','reason':'literal text'}])
    assert repaired['edges'][0]==dict(original['edges'][0],quote='A supplies B.')
    assert original['edges'][0]['quote']=='A sells to B'
    assert changes[0]['action']=='replace_quote'


def test_model_added_kind_cannot_change_target_identity():
    from reviewer_analysis.revision_v2.quote_patch import invalid_quote_targets
    original=graph();original['edges'][0]['kind']='nodes'
    assert invalid_quote_targets(original,'A supplies B.')[0]['kind']=='edges'


def test_unsupported_node_cannot_remove_unreviewed_incident_edges():
    from reviewer_analysis.revision_v2.quote_patch import apply_quote_patches
    original=graph();original['nodes'][1]['quote']='unsupported B'
    original['edges'][0]['quote']='A supplies B.'
    with pytest.raises(ValueError,match='unreviewed edge'):
        apply_quote_patches(original,'A supplies B.',[
            {'kind':'nodes','id':'b','quote':None,'reason':'entity not established at claimed scope'}])
    assert len(original['nodes'])==2 and len(original['edges'])==1


@pytest.mark.parametrize('patches',[
    [{'kind':'edges','id':'e','quote':'invented quote','reason':'x'}],
    [],
    [{'kind':'nodes','id':'a','quote':'A','reason':'x'}],
    [{'kind':'edges','id':'e','quote':'A supplies B.','reason':'x'}]*2,
])
def test_missing_extra_duplicate_or_invented_patches_rejected(patches):
    from reviewer_analysis.revision_v2.quote_patch import apply_quote_patches
    with pytest.raises(ValueError):apply_quote_patches(graph(),'A supplies B.',patches)


def test_interrupted_repair_is_not_automatically_reinvoked(tmp_path,monkeypatch):
    import importlib.util
    import json
    from pathlib import Path
    from reviewer_analysis.revision_v2.common import write_json
    private=Path(__file__).resolve().parents[1]/'private'
    if not (private/'run_quote_patch.py').is_file():
        pytest.skip('Private batch orchestration is not part of the published evaluator package')
    monkeypatch.setenv('REVIEW_JUDGE_MODEL','gpt-5.5')
    monkeypatch.setenv('REVIEW_CODEX_TIMEOUT','600')
    monkeypatch.syspath_prepend(str(private))
    spec=importlib.util.spec_from_file_location('repair_fixture',private/'run_quote_patch.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.BASE=tmp_path/'batch';module.OUT=tmp_path/'repair'
    task={'key':['test','one','Q61'],'quadrant':'Q4','record_hash':'fixture',
          'payload':{'question':'q','report':'A supplies B.'}}
    monkeypatch.setattr(module,'scan',lambda:[{'task':task,'raw_response':json.dumps(graph())}])
    class Client:
        public_config={'backend':'fixture'}
        calls=0
        def __init__(self,*args):pass
        def chat(self,*args):
            Client.calls+=1
            if Client.calls==1:raise KeyboardInterrupt()
            return json.dumps({'repairs':[{'kind':'edges','id':'e','quote':'A supplies B.','reason':'exact'}]}),{},None
    monkeypatch.setattr(module,'CodexClient',Client)
    write_json(module.BASE/'protocol.json',{'client':Client.public_config})
    for shard in (0,1):write_json(module.BASE/f'progress/extract_{shard}.json',{'status':'complete'})
    with pytest.raises(KeyboardInterrupt):module.main(True)
    with pytest.raises(RuntimeError,match='attempt'):module.main(True)
    assert Client.calls==1
