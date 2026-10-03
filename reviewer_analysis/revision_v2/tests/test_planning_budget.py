from concurrent.futures import ThreadPoolExecutor
import json

import pytest

from reviewer_analysis.revision_v2 import planning_budget as b


def test_parallel_reservations_protect_final_allowance(tmp_path):
    ledger = b.BudgetLedger(total_tokens=100, final_tokens=20,
                            search_requests=3, page_requests=4,
                            journal=tmp_path / 'ledger.jsonl')
    def attempt(_):
        try:
            return ledger.reserve_tokens(input_tokens=10, max_output_tokens=10)
        except b.BudgetExceeded:
            return None
    with ThreadPoolExecutor(max_workers=12) as pool:
        accepted = [x for x in pool.map(attempt, range(30)) if x is not None]
    assert len(accepted) == 4
    with pytest.raises(b.BudgetError):
        ledger.begin_final()
    for ticket in accepted:
        ledger.settle_tokens(ticket, input_tokens=10, output_tokens=10)
    ledger.begin_final()
    with pytest.raises(b.BudgetError):
        ledger.reserve_tokens(input_tokens=1, max_output_tokens=1)
    ticket = ledger.reserve_tokens(input_tokens=10, max_output_tokens=10, final=True)
    ledger.settle_tokens(ticket, input_tokens=10, output_tokens=10)
    assert ledger.snapshot()['charged_tokens'] == 100
    assert len([r for r in map(json.loads, (tmp_path/'ledger.jsonl').read_text().splitlines())
                if r['event'] == 'token_reserved']) == 5


def test_failed_attempt_is_not_free_and_unknown_is_distinct_from_actual():
    ledger = b.BudgetLedger(100, 20, 2, 2)
    ticket = ledger.reserve_tokens(input_tokens=10, max_output_tokens=40)
    ledger.settle_tokens(ticket)  # timeout: retain full conservative charge
    ticket2 = ledger.reserve_tokens(input_tokens=10, max_output_tokens=20)
    ledger.settle_tokens(ticket2, input_tokens=10, output_tokens=5)
    state = ledger.snapshot()
    assert state['charged_tokens'] == 65
    assert state['known_actual_tokens'] == 15
    assert state['unknown_usage_attempts'] == 1
    with pytest.raises(b.BudgetError):
        ledger.settle_tokens(ticket, input_tokens=0, output_tokens=0)


def test_search_and_page_failures_consume_actual_attempt_slots():
    ledger = b.BudgetLedger(100, 20, 2, 1)
    ledger.reserve_request('search')
    ledger.reserve_request('search')  # retry is a second dispatched attempt
    with pytest.raises(b.BudgetExceeded):
        ledger.reserve_request('search')
    ledger.reserve_request('page')
    with pytest.raises(b.BudgetExceeded):
        ledger.reserve_request('page')
    assert ledger.snapshot()['requests'] == {'search': 2, 'page': 1}


def test_provider_exceeding_reservation_halts_future_dispatch():
    ledger = b.BudgetLedger(100, 20, 2, 2)
    ticket = ledger.reserve_tokens(input_tokens=10, max_output_tokens=10)
    with pytest.raises(b.BudgetError):
        ledger.settle_tokens(ticket, input_tokens=11, output_tokens=10)
    assert ledger.snapshot()['violation'] is True
    with pytest.raises(b.BudgetError):
        ledger.reserve_request('search')


@pytest.mark.parametrize('bad', [-1, True, 1.5, '2'])
def test_invalid_usage_never_releases_reserved_capacity(bad):
    ledger = b.BudgetLedger(100, 20, 2, 2)
    ticket = ledger.reserve_tokens(input_tokens=10, max_output_tokens=10)
    with pytest.raises((ValueError, b.BudgetError)):
        ledger.settle_tokens(ticket, input_tokens=10, output_tokens=bad)
    assert ledger.snapshot()['charged_tokens'] == 20


def test_existing_journal_cannot_be_silently_reused(tmp_path):
    journal = tmp_path/'run.jsonl'
    journal.write_text('old run\n')
    with pytest.raises(FileExistsError):
        b.BudgetLedger(100, 20, 2, 2, journal=journal)
    assert journal.read_text() == 'old run\n'
