import importlib.util
import json
from pathlib import Path
import pytest


def module():
    path=Path(__file__).with_name('repair.py')
    spec=importlib.util.spec_from_file_location('match_repair',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def failed():
    g={'nodes':[{'id':'a'},{'id':'b'}],'edges':[{'id':'ab','source_id':'a','target_id':'b','relation_type':'supplies'}]}
    return {'task':{'key':['method','run','Q61'],'quadrant':'Q4','payload':{'predicted_graph':g,'reference_graph':g,'scope':{}},
                    'reference_hash':'ref','prediction_hash':'pred'},'error':'Relation match contradicts directed endpoint mapping',
            'error_kind':'content_validation','raw_response':'{"node_matches":[],"edge_matches":[["ab","ab"]]}'}


class Client:
    def __init__(self,answer):self.answer=answer;self.n=0
    def chat(self,system,payload):self.n+=1;return json.dumps(self.answer),{'cli_call_id':'test'},None


def test_valid_repair_preserves_primary_and_scores_real_pairs(tmp_path):
    m=module();old=failed();before=json.dumps(old,sort_keys=True)
    c=Client({'node_matches':[['a','a'],['b','b']],'edge_matches':[['ab','ab']]})
    r=m.repair_once(old,tmp_path/'repair',c)
    assert json.dumps(old,sort_keys=True)==before
    assert r['result']['graph_f1']==1 and r['result']['matched_edges']==1
    assert r['repair_of_sha256']==m.digest(old)
    assert m.repair_once(old,tmp_path/'repair',c)==r and c.n==1


def test_invalid_repair_is_retained_and_never_silently_scored(tmp_path):
    m=module();c=Client({'node_matches':[['a','a']],'edge_matches':[['ab','ab']]})
    r=m.repair_once(failed(),tmp_path/'repair',c)
    assert 'error' in r and 'result' not in r and 'raw_response' in r
    assert m.repair_once(failed(),tmp_path/'repair',c)==r and c.n==1


def test_interrupted_repair_cannot_spend_again(tmp_path):
    m=module();dest=tmp_path/'repair';dest.mkdir();(dest/'attempt.json').write_text('{}')
    c=Client({})
    with pytest.raises(FileExistsError):m.repair_once(failed(),dest,c)
    assert c.n==0
