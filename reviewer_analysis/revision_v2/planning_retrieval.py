"""Strict, shared SEARCH/PAGE attempt accounting for isolated native workers.

Install after importing ``agent.core.tools`` and before starting worker threads.
The requests HTTPAdapter boundary reserves durably before transport; redirects,
application retries, errors and Jina fallbacks each consume another slot. Hidden
urllib3 retries and custom adapters are rejected, since they bypass that boundary.

Both experiment arms explicitly disable Playwright page fallback and optional OCR.
Only Serper POST search and HTTP(S) GET page retrieval are permitted here. Known
alternate search/model hosts are denied. This is an experiment instrumentation
boundary for the audited native requests paths, not a general OS network sandbox.
It does not patch subprocess networking (in particular the Codex child process).
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter


class RetrievalBudgetExceeded(RuntimeError):
    """The shared request allowance was exhausted before transport."""


class RetrievalPolicyError(RuntimeError):
    """Unmetered or disallowed network activity was refused."""


_DENIED_HOSTS = (
    'serpapi.com', 'duckduckgo.com', 'bing.com', 'api.bing.microsoft.com',
    'api.search.brave.com', 'googleapis.com', 'google.com',
    'siliconflow.cn', 'siliconflow.com', 'dashscope.aliyuncs.com',
    'dashscope-intl.aliyuncs.com', 'api.openai.com', 'api.anthropic.com',
    'api.deepseek.com', 'huggingface.co', 'hf.co',
)
_INSTALL_LOCK = threading.Lock()


def _safe_url(url):
    """Never persist credentials, query text, path tokens or request bodies."""
    parts = urlsplit(url)
    return {'host': parts.hostname or '',
            'url_sha256': hashlib.sha256(url.encode('utf8')).hexdigest()}


def _classify(request):
    parts = urlsplit(request.url)
    host = (parts.hostname or '').lower().rstrip('.')
    if parts.scheme not in ('http', 'https') or not host:
        raise RetrievalPolicyError('Only HTTP(S) retrieval is enabled')
    if host == 'google.serper.dev':
        if parts.scheme == 'https' and parts.path == '/search' and request.method == 'POST':
            return 'search'
        raise RetrievalPolicyError('Only the configured Serper search endpoint is enabled')
    if any(host == domain or host.endswith('.' + domain) for domain in _DENIED_HOSTS):
        raise RetrievalPolicyError('Alternate search, model, and model-download endpoints are disabled')
    if request.method != 'GET':
        raise RetrievalPolicyError('Page retrieval permits GET only')
    if host == 'r.jina.ai':
        # Jina must not be usable as an alternate search-provider proxy.
        target = parts.path.lstrip('/')
        if target.startswith(('http://', 'https://')):
            nested = requests.Request('GET', target).prepare()
            _classify(nested)
    return 'page'


class RetrievalMeter:
    """Thread-safe attempt ledger; successful responses do not refund failures."""

    def __init__(self, search_limit, page_limit, journal=None):
        for name, value in (('search_limit', search_limit), ('page_limit', page_limit)):
            if type(value) is not int or value < 0:
                raise ValueError(f'{name} must be a nonnegative integer')
        self._limits = {'search': search_limit, 'page': page_limit}
        self._requests = {'search': 0, 'page': 0}
        self._lock = threading.RLock()
        self._pending = set()
        self._next_ticket = 0
        self._blocked = 0
        self._violation = False
        self.journal = Path(journal) if journal is not None else None
        if self.journal is not None:
            self.journal.parent.mkdir(parents=True, exist_ok=True)
            # Never overwrite an earlier run's evidence.
            with self.journal.open('x', encoding='utf8'):
                pass
        self._record('retrieval_meter_created', limits=dict(self._limits),
                     playwright_page_fallback=False, page_ocr=False,
                     hidden_http_retries=False)

    def _record(self, event, **fields):
        if self.journal is None:
            return
        try:
            with self.journal.open('a', encoding='utf8') as stream:
                stream.write(json.dumps({'event': event, **fields}, sort_keys=True) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            self._violation = True
            raise

    def _reserve(self, kind, request):
        with self._lock:
            if self._violation:
                raise RetrievalPolicyError('Retrieval accounting failed; dispatch halted')
            if self._requests[kind] >= self._limits[kind]:
                self._blocked += 1
                self._record('request_blocked', kind=kind, reason='allowance_exhausted',
                             **_safe_url(request.url))
                raise RetrievalBudgetExceeded(f'{kind.upper()} allowance exhausted')
            ticket = self._next_ticket
            self._record('request_reserved', ticket=ticket, kind=kind,
                         attempt=self._requests[kind] + 1, method=request.method,
                         **_safe_url(request.url))
            self._next_ticket += 1
            self._requests[kind] += 1
            self._pending.add(ticket)
            return ticket

    def _finish(self, ticket, *, status_code=None, error_type=None):
        with self._lock:
            self._record('request_finished', ticket=ticket,
                         outcome='error' if error_type else 'response',
                         status_code=status_code, error_type=error_type)
            self._pending.remove(ticket)

    def _deny(self, request, reason):
        with self._lock:
            self._blocked += 1
            self._record('request_blocked', reason=reason, **_safe_url(request.url))
        raise RetrievalPolicyError(reason)

    @property
    def exhausted(self):
        """True when either retrieval allowance has been reached."""
        with self._lock:
            return any(self._requests[kind] >= self._limits[kind] for kind in self._limits)

    def snapshot(self):
        with self._lock:
            return {'requests': dict(self._requests), 'limits': dict(self._limits),
                    'pending_attempts': len(self._pending),
                    'blocked_attempts': self._blocked, 'exhausted': self.exhausted,
                    'violation': self._violation}


@contextmanager
def install_retrieval_meter(meter):
    """Install worker-global guards, then restore every patch even on failure.

    Contexts must not overlap within one process. Each arm uses a fresh process,
    with native tools imported before entry. Standard requests sessions, including
    sessions created before entry, share this meter. All worker threads must join
    before leaving the context.
    """
    if not isinstance(meter, RetrievalMeter):
        raise TypeError('meter must be a RetrievalMeter')
    if not _INSTALL_LOCK.acquire(blocking=False):
        raise RetrievalPolicyError('A retrieval meter is already installed')
    patches = []
    previous_ocr = os.environ.get('ENABLE_PAGE_OCR')
    original_send = HTTPAdapter.send
    original_session_send = requests.Session.send

    def patch(owner, name, replacement):
        patches.append((owner, name, getattr(owner, name)))
        setattr(owner, name, replacement)

    def check_adapter(adapter, request):
        # Retry(total=0) covers the standard adapter default. Refuse adapters
        # that could perform retries inside one counted send call.
        if adapter.max_retries.total not in (0, False):
            meter._deny(request, 'Hidden HTTP retries are disabled')

    def metered_send(adapter, request, **kwargs):
        check_adapter(adapter, request)
        try:
            kind = _classify(request)
        except RetrievalPolicyError:
            meter._deny(request, 'Endpoint or method is outside retrieval policy')
        ticket = meter._reserve(kind, request)
        try:
            response = original_send(adapter, request, **kwargs)
        except BaseException as exc:
            meter._finish(ticket, error_type=type(exc).__name__)
            raise
        meter._finish(ticket, status_code=response.status_code)
        return response

    def guarded_session_send(session, request, **kwargs):
        adapter = session.get_adapter(request.url)
        if not isinstance(adapter, HTTPAdapter) or getattr(adapter.send, '__func__', None) is not metered_send:
            meter._deny(request, 'Custom HTTP adapters are disabled')
        return original_session_send(session, request, **kwargs)

    def no_browser(*args, **kwargs):
        raise RetrievalPolicyError('Playwright retrieval is disabled for both arms')

    def no_alternate_search(*args, **kwargs):
        raise RetrievalPolicyError('Only Serper search is enabled for both arms')

    def no_optional_content(*args, **kwargs):
        return ''

    try:
        patch(HTTPAdapter, 'send', metered_send)
        patch(requests.Session, 'send', guarded_session_send)
        os.environ['ENABLE_PAGE_OCR'] = 'false'
        # Avoid importing heavy native backends here. Workers must import native
        # tools first; these aliases cover the source package and worker import.
        visited = set()
        for name in ('agent.core.tools', 'helix_core.agent.core.tools'):
            module = sys.modules.get(name)
            if module is None or id(module) in visited:
                continue
            visited.add(id(module))
            if hasattr(module, '_get_playwright_browser'):
                patch(module, '_get_playwright_browser', no_browser)
            page = getattr(module, 'PageSelectTool', None)
            for method in ('_fetch_with_playwright_pdf', '_ocr_single_image'):
                if page is not None and hasattr(page, method):
                    patch(page, method, no_optional_content)
            search = getattr(module, 'WebSearchTool', None)
            for method in ('_search_serpapi', '_search_duckduckgo', '_search_bing', '_search_google'):
                if search is not None and hasattr(search, method):
                    patch(search, method, no_alternate_search)
        yield meter
    finally:
        for owner, name, original in reversed(patches):
            setattr(owner, name, original)
        if previous_ocr is None:
            os.environ.pop('ENABLE_PAGE_OCR', None)
        else:
            os.environ['ENABLE_PAGE_OCR'] = previous_ocr
        _INSTALL_LOCK.release()
