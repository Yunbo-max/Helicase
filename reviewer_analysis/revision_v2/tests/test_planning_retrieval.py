"""Real requests dispatch with only the external HTTP transport replaced."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import sys
from types import ModuleType

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from reviewer_analysis.revision_v2 import planning_retrieval as p


@pytest.fixture
def transport(monkeypatch):
    sent = []
    def send(adapter, request, **kwargs):
        sent.append(request.url)
        if '/failure' in request.url:
            raise requests.ConnectionError('secret-token-in-transport-error')
        response = requests.Response()
        response.request = request
        response.url = request.url
        response.status_code = 302 if '/redirect' in request.url else 200
        if response.status_code == 302:
            response.headers['Location'] = 'https://publisher.test/article'
        response._content = b'ok'
        response._content_consumed = True
        return response
    monkeypatch.setattr(HTTPAdapter, 'send', send)
    return sent


def test_reserves_before_dispatch_and_does_not_refund_failure(transport, tmp_path):
    journal = tmp_path / 'retrieval.jsonl'
    meter = p.RetrievalMeter(2, 1, journal)
    with p.install_retrieval_meter(meter):
        for _ in range(2):
            requests.post('https://google.serper.dev/search', json={'q': 'secret query'})
        with pytest.raises(p.RetrievalBudgetExceeded):
            requests.post('https://google.serper.dev/search')
        with pytest.raises(requests.ConnectionError):
            requests.get('https://publisher.test/failure?token=secret')
        with pytest.raises(p.RetrievalBudgetExceeded):
            requests.get('https://r.jina.ai/https://publisher.test/article')
    assert len(transport) == 3
    assert meter.snapshot()['requests'] == {'search': 2, 'page': 1}
    assert meter.snapshot()['pending_attempts'] == 0
    assert meter.exhausted
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    assert len([e for e in events if e['event'] == 'request_reserved']) == 3
    assert [e['outcome'] for e in events if e['event'] == 'request_finished'] == ['response', 'response', 'error']
    assert 'secret' not in journal.read_text()
    snapshot = meter.snapshot()
    snapshot['requests']['search'] = 999
    assert meter.snapshot()['requests']['search'] == 2
    with pytest.raises(FileExistsError):
        p.RetrievalMeter(2, 1, journal)


def test_redirect_is_separate_page_attempt_and_budget_blocks_destination(transport):
    meter = p.RetrievalMeter(2, 1)
    with p.install_retrieval_meter(meter):
        with pytest.raises(p.RetrievalBudgetExceeded):
            requests.get('https://publisher.test/redirect')
    assert transport == ['https://publisher.test/redirect']
    assert meter.snapshot()['requests']['page'] == 1
    assert meter.snapshot()['pending_attempts'] == 0


def test_redirect_success_and_jina_fallback_are_all_counted(transport):
    meter = p.RetrievalMeter(0, 3)
    with p.install_retrieval_meter(meter):
        response = requests.get('https://publisher.test/redirect')
        requests.get('https://r.jina.ai/https://publisher.test/article')
    assert len(response.history) == 1
    assert meter.snapshot()['requests'] == {'search': 0, 'page': 3}
    assert len(transport) == 3


def test_concurrent_calls_share_strict_cap(transport):
    meter = p.RetrievalMeter(7, 0)
    def search(_):
        try:
            requests.post('https://google.serper.dev/search')
            return True
        except p.RetrievalBudgetExceeded:
            return False
    with p.install_retrieval_meter(meter):
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(search, range(40)))
    assert sum(results) == len(transport) == 7
    assert meter.snapshot()['requests']['search'] == 7


@pytest.mark.parametrize('url,method', [
    ('https://serpapi.com/search.json', 'GET'),
    ('https://duckduckgo.com/?q=x', 'GET'),
    ('https://www.googleapis.com/customsearch/v1', 'GET'),
    ('https://api.siliconflow.cn/v1/chat/completions', 'POST'),
    ('https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation', 'POST'),
    ('https://r.jina.ai/https://duckduckgo.com/?q=x', 'GET'),
    ('https://unapproved.test/inference', 'POST'),
    ('https://google.serper.dev/other', 'POST'),
])
def test_disallowed_providers_do_not_dispatch(transport, url, method):
    meter = p.RetrievalMeter(3, 3)
    with p.install_retrieval_meter(meter):
        with pytest.raises(p.RetrievalPolicyError):
            requests.request(method, url)
    assert transport == []
    assert meter.snapshot()['requests'] == {'search': 0, 'page': 0}


def test_retrying_adapter_is_rejected_to_prevent_hidden_attempts(transport):
    meter = p.RetrievalMeter(1, 1)
    with requests.Session() as session:
        session.mount('https://', HTTPAdapter(max_retries=Retry(total=3)))
        with p.install_retrieval_meter(meter):
            with pytest.raises(p.RetrievalPolicyError):
                session.get('https://publisher.test/article')
    assert transport == []


def test_custom_adapter_cannot_bypass_meter(transport):
    class CustomAdapter(HTTPAdapter):
        def send(self, request, **kwargs):
            raise AssertionError('Unmetered custom adapter was dispatched')
    meter = p.RetrievalMeter(1, 1)
    with requests.Session() as session:
        session.mount('https://', CustomAdapter())
        with p.install_retrieval_meter(meter):
            with pytest.raises(p.RetrievalPolicyError):
                session.get('https://publisher.test/article')
    assert transport == []


def test_native_browser_ocr_and_alternate_search_disabled_and_restored(monkeypatch, transport):
    # Lightweight native module surface: no imports of model/embedding backends.
    native = ModuleType('agent.core.tools')
    class PageSelectTool:
        def _fetch_with_playwright_pdf(self, url):
            return 'browser called'
        def _ocr_single_image(self, image):
            return 'ocr called'
    class WebSearchTool:
        def _search_duckduckgo(self):
            return ['unmetered result']
    native.PageSelectTool = PageSelectTool
    native.WebSearchTool = WebSearchTool
    native._get_playwright_browser = lambda: 'browser'
    monkeypatch.setitem(sys.modules, 'agent.core.tools', native)
    monkeypatch.setenv('ENABLE_PAGE_OCR', 'true')
    original = requests.Session.send
    meter = p.RetrievalMeter(1, 1)
    with pytest.raises(RuntimeError, match='abort'):
        with p.install_retrieval_meter(meter):
            assert os.environ['ENABLE_PAGE_OCR'] == 'false'
            assert PageSelectTool()._fetch_with_playwright_pdf('https://test') == ''
            assert PageSelectTool()._ocr_single_image({}) == ''
            with pytest.raises(p.RetrievalPolicyError):
                WebSearchTool()._search_duckduckgo()
            with pytest.raises(p.RetrievalPolicyError):
                native._get_playwright_browser()
            raise RuntimeError('abort')
    assert requests.Session.send is original
    assert os.environ['ENABLE_PAGE_OCR'] == 'true'
    assert PageSelectTool()._fetch_with_playwright_pdf('https://test') == 'browser called'
    assert WebSearchTool()._search_duckduckgo() == ['unmetered result']


def test_failed_journal_write_halts_dispatch(transport, tmp_path):
    journal = tmp_path / 'attempts.jsonl'
    meter = p.RetrievalMeter(2, 2, journal)
    journal.unlink()
    journal.mkdir()
    with p.install_retrieval_meter(meter):
        with pytest.raises(OSError):
            requests.get('https://publisher.test/article')
        with pytest.raises(p.RetrievalPolicyError):
            requests.get('https://publisher.test/another')
    assert transport == []
    assert meter.snapshot()['violation']


def test_reservation_is_durable_when_transport_starts(monkeypatch, tmp_path):
    journal = tmp_path / 'attempts.jsonl'
    meter = p.RetrievalMeter(1, 1, journal)
    def send(adapter, request, **kwargs):
        recorded = [json.loads(line) for line in journal.read_text().splitlines()]
        assert recorded[-1]['event'] == 'request_reserved'
        assert recorded[-1]['kind'] == 'page'
        assert meter.snapshot()['requests']['page'] == 1
        assert meter.snapshot()['pending_attempts'] == 1
        raise requests.Timeout('credentials must not be recorded')
    monkeypatch.setattr(HTTPAdapter, 'send', send)
    with p.install_retrieval_meter(meter):
        with pytest.raises(requests.Timeout):
            requests.get('https://publisher.test/article')
    assert meter.snapshot()['pending_attempts'] == 0
    assert 'credentials' not in journal.read_text()


def test_application_retry_after_failure_is_another_attempt(transport):
    meter = p.RetrievalMeter(2, 2)
    with p.install_retrieval_meter(meter):
        for _ in range(2):
            with pytest.raises(requests.ConnectionError):
                requests.get('https://publisher.test/failure')
        with pytest.raises(p.RetrievalBudgetExceeded):
            requests.get('https://publisher.test/failure')
    assert len(transport) == 2
    assert meter.snapshot()['requests']['page'] == 2


def test_nested_installation_cannot_replace_or_remove_outer_guard(transport):
    meter = p.RetrievalMeter(1, 1)
    with p.install_retrieval_meter(meter):
        with pytest.raises(p.RetrievalPolicyError):
            with p.install_retrieval_meter(p.RetrievalMeter(100, 100)):
                pytest.fail('Nested installation must not be allowed')
        requests.get('https://publisher.test/article')
        with pytest.raises(p.RetrievalBudgetExceeded):
            requests.get('https://publisher.test/article')
    assert len(transport) == 1


@pytest.mark.parametrize('limit', [-1, 1.5, True, '2'])
def test_invalid_allowances_rejected(limit):
    with pytest.raises(ValueError):
        p.RetrievalMeter(limit, 1)
    with pytest.raises(ValueError):
        p.RetrievalMeter(1, limit)
