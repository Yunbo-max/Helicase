"""Review byte-preserved completed evaluation traces without changing model requests."""
import json
import re
from pathlib import Path
from .common import digest


def validate_completed_trace(directory, expected_prompt):
    directory = Path(directory)
    request = json.loads((directory/'request.json').read_text())
    if ((directory/'prompt.txt').read_text() != expected_prompt
            or request['input_sha256'] != digest(expected_prompt)
            or request['config']['requested_model'] != 'gpt-5.5'):
        raise ValueError('Trace input/model mismatch')
    exit_record = json.loads((directory/'exit.json').read_text())
    if exit_record.get('returncode') != 0 or exit_record.get('timed_out') is not False:
        raise ValueError('Incomplete process')
    events = [json.loads(line) for line in (directory/'events.jsonl').read_text().split('\n') if line.strip()]
    errors = [e for e in events if e.get('type') == 'error']
    reconnect = re.compile(r'Reconnecting\.\.\. [1-5]/5 \(unexpected status 403 Forbidden: Unknown error, '
                           r'url: wss://chatgpt\.com/backend-api/codex/responses, cf-ray: [A-Za-z0-9-]+\)')
    if (any(not reconnect.fullmatch(e.get('message','')) for e in errors)
            or any(e.get('type') == 'turn.failed' for e in events)):
        raise ValueError('Unaccepted error event')
    fallback = re.compile(r'Falling back from WebSockets to HTTPS transport\. unexpected status 403 Forbidden: '
                          r'Unknown error, url: wss://chatgpt\.com/backend-api/codex/responses, cf-ray: [A-Za-z0-9-]+')
    for event in events:
        if not event.get('type','').startswith('item.'):
            continue
        item = event.get('item', {})
        if item.get('type') in ('agent_message','reasoning'):
            continue
        if (event['type'] == 'item.completed' and item.get('type') == 'error'
                and fallback.fullmatch(item.get('message',''))):
            continue
        raise ValueError('Unexpected tool or item event')
    completed = [e for e in events if e.get('type') == 'turn.completed']
    if len(completed) != 1 or events[-1].get('type') != 'turn.completed':
        raise ValueError('Expected one terminal completed turn')
    usage = completed[0].get('usage', {})
    if any(type(usage.get(k)) is not int or usage[k] < 0 for k in ('input_tokens','output_tokens')):
        raise ValueError('Invalid usage')
    answer = (directory/'answer.txt').read_text()
    messages = [e['item'].get('text') for e in events if e.get('type') == 'item.completed'
                and e.get('item',{}).get('type') == 'agent_message']
    if not messages or not isinstance(messages[-1],str) or answer.strip() != messages[-1].strip():
        raise ValueError('Final output mismatch')
    return answer, dict(usage, cli_call_id=directory.name), {'recovered_websocket_errors': len(errors)}
