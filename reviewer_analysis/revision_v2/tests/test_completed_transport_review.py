import json
import pytest
from reviewer_analysis.revision_v2.common import digest
from reviewer_analysis.revision_v2.completed_transport_review import validate_completed_trace

ERROR={'type':'error','message':'Reconnecting... 2/5 (unexpected status 403 Forbidden: Unknown error, url: wss://chatgpt.com/backend-api/codex/responses, cf-ray: a45acc84793250f1-LHR)'}

def fixture(tmp_path, *, error=ERROR):
    events=[{'type':'thread.started'},{'type':'turn.started'}]
    if error:events.append(error)
    events += [{'type':'item.completed','item':{'type':'agent_message','text':'["answer"]'}},
               {'type':'turn.completed','usage':{'input_tokens':12,'output_tokens':3}}]
    (tmp_path/'prompt.txt').write_text('prompt')
    (tmp_path/'request.json').write_text(json.dumps({'input_sha256':digest('prompt'),'config':{'requested_model':'gpt-5.5'}}))
    (tmp_path/'exit.json').write_text(json.dumps({'returncode':0,'timed_out':False}))
    (tmp_path/'answer.txt').write_text('["answer"]')
    save(tmp_path,events)
    return events

def save(path,events):
    (path/'events.jsonl').write_text('\n'.join(json.dumps(e) for e in events)+'\n')

def test_completed_websocket_reconnect_preserves_answer_and_usage(tmp_path):
    fixture(tmp_path)
    answer,usage,review=validate_completed_trace(tmp_path,'prompt')
    assert answer=='["answer"]' and usage['input_tokens']==12
    assert review['recovered_websocket_errors']==1

@pytest.mark.parametrize('error',[
    {'type':'error','message':'content_policy_violation'},
    {'type':'error','message':'403 Forbidden https://other.example'},
    {'type':'turn.failed','error':{'message':'failed'}},
    {'type':'error','message':ERROR['message']+' content_filter'},
])
def test_rejects_other_errors_even_with_completed_turn(tmp_path,error):
    fixture(tmp_path,error=error)
    with pytest.raises(ValueError):validate_completed_trace(tmp_path,'prompt')

@pytest.mark.parametrize('mutation',['answer','prompt','exit','tool','usage','duplicate','incomplete'])
def test_requires_all_completion_and_provenance_checks(tmp_path,mutation):
    events=fixture(tmp_path,error=None)
    if mutation=='answer':(tmp_path/'answer.txt').write_text('different')
    if mutation=='prompt':(tmp_path/'prompt.txt').write_text('different')
    if mutation=='exit':(tmp_path/'exit.json').write_text('{"returncode": 1, "timed_out": false}')
    if mutation=='tool':events.insert(2,{'type':'item.completed','item':{'type':'command_execution'}})
    if mutation=='usage':events[-1]['usage']['input_tokens']=True
    if mutation=='duplicate':events.append(events[-1])
    if mutation=='incomplete':events.pop()
    save(tmp_path,events)
    with pytest.raises(ValueError):validate_completed_trace(tmp_path,'prompt')


def test_accepts_exact_transport_fallback_notification(tmp_path):
    events=fixture(tmp_path)
    events.insert(3,{'type':'item.completed','item':{'type':'error','message':'Falling back from WebSockets to HTTPS transport. unexpected status 403 Forbidden: Unknown error, url: wss://chatgpt.com/backend-api/codex/responses, cf-ray: a45adb1f1f3ec616-LHR'}})
    save(tmp_path,events)
    assert validate_completed_trace(tmp_path,'prompt')[0]=='["answer"]'


def test_rejects_other_error_item_notifications(tmp_path):
    events=fixture(tmp_path,error=None)
    events.insert(2,{'type':'item.completed','item':{'type':'error','message':'content_filter'}})
    save(tmp_path,events)
    with pytest.raises(ValueError):validate_completed_trace(tmp_path,'prompt')
