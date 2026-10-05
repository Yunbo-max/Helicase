"""Explicit, offline quote-format recovery; never changes frozen evaluators."""
import json

from .answer_blind import extract_transform


def reconcile_article_case(raw_response, task):
    """Reconcile only a unique The/the quote span; retain all answer semantics.

    This is an explicit post-run recovery, not part of the frozen V4 evaluator.
    Callers must retain the original response and disclose the derived response.
    It performs no model calls and cannot read reference answers or scores.
    """
    obj = json.loads(raw_response)
    try:
        return raw_response, extract_transform(obj, task), []
    except ValueError as exc:
        if str(exc) != 'Non-exact quotation':
            raise
    sources = {r['source_id']: r['text'] for r in task['payload']['reports']}
    corrections = []

    def recover(quote, source_id, path):
        text = sources[source_id]
        if isinstance(quote, str) and quote.strip() and quote in text:
            return quote
        if not isinstance(quote, str) or not quote.startswith(('The ', 'the ')):
            raise ValueError('Quote is outside the leading-article recovery scope')
        candidate = quote[0].swapcase() + quote[1:]
        offset = text.find(candidate)
        if offset < 0 or text.find(candidate, offset + 1) >= 0:
            raise ValueError('Recovery requires one exact source span')
        corrections.append({'path': path, 'source_id': source_id,
                            'original_quote': quote, 'source_quote': candidate,
                            'source_offset': offset})
        return candidate

    for i, report in enumerate(obj['reports']):
        sid = report['source_id']
        if sid not in sources:
            raise ValueError('Unknown source')
        for j, answer in enumerate(report['answers']):
            answer['quotes'] = [recover(q, sid, f'reports/{i}/answers/{j}/quotes/{k}')
                                for k, q in enumerate(answer['quotes'])]
        for j, excluded in enumerate(report['excluded']):
            excluded['quote'] = recover(excluded['quote'], sid,
                                        f'reports/{i}/excluded/{j}/quote')
    result = extract_transform(obj, task)
    return json.dumps(obj, ensure_ascii=False), result, corrections
