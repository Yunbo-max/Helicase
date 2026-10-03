import importlib.util
from pathlib import Path
import json
import pytest


def module():
    path=Path(__file__).with_name('run_draft.py')
    assert path.exists(), 'Reference draft driver missing'
    spec=importlib.util.spec_from_file_location('reference_draft_test',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod


def packet():
    return {'query_id':'Q61','question':'Which supplier?','existing_text_answer':'A supplies B.',
            'existing_source_urls':[],'status':'author_review_required_not_gold',
            'reference_version':None,'draft_reference_graph':None,'author_completeness_confirmation':None}


def graph():
    return {'nodes':[{'id':'a','name':'A','node_type':'company','quote':'A supplies B.'},
                     {'id':'b','name':'B','node_type':'company','quote':'A supplies B.'}],
            'edges':[{'id':'e','source_id':'a','target_id':'b','relation_type':'supplies',
                      'evidence_status':'reported','quote':'A supplies B.'}]}


def test_draft_cannot_become_author_confirmed_gold(tmp_path):
    m=module()
    class Client:
        def chat(self,system,payload):
            assert set(payload)=={'question','report'}
            assert payload['report']=='A supplies B.'
            return json.dumps(dict(graph(),author_completeness_confirmation=True,reference_version='gold')),{},None
    r=m.evaluate(packet(),tmp_path,Client())
    assert r['result']['author_completeness_confirmation'] is None
    assert r['result']['reference_version'] is None
    assert r['result']['status']=='draft_from_original_text_requires_author_review'
    assert r['result']['draft_reference_graph']==graph()


def test_invented_quote_fails_and_is_not_silently_retried(tmp_path):
    m=module()
    class Client:
        calls=0
        def chat(self,*args):
            self.calls+=1;g=graph();g['edges'][0]['quote']='B supplies A.'
            return json.dumps(g),{},None
    c=Client();a=m.evaluate(packet(),tmp_path,c);b=m.evaluate(packet(),tmp_path,c)
    assert 'error' in a and a==b and c.calls==1


def test_interrupted_attempt_requires_inspection(tmp_path):
    m=module()
    class Client:
        def chat(self,*args):raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):m.evaluate(packet(),tmp_path,Client())
    with pytest.raises(FileExistsError):m.evaluate(packet(),tmp_path,Client())
