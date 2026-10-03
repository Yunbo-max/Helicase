"""Experiment budget ledger; not a backend or proof of dispatch integration.

Adapters MUST reserve before each actual attempt, bound provider output, disable
hidden retries, and settle even failures. Unknown usage remains fully charged.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import threading


class BudgetError(RuntimeError):
    pass


class BudgetExceeded(BudgetError):
    pass


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


class BudgetLedger:
    def __init__(self, total_tokens, final_tokens, search_requests, page_requests,
                 journal=None):
        self.total = _integer(total_tokens, 'total_tokens', 1)
        self.final = _integer(final_tokens, 'final_tokens', 1)
        if self.final >= self.total:
            raise ValueError('Final allowance must be smaller than total budget')
        self.limits = {'search': _integer(search_requests, 'search_requests'),
                       'page': _integer(page_requests, 'page_requests')}
        self.requests = {'search': 0, 'page': 0}
        self._lock = threading.RLock()
        self._pending = {}
        self._next_ticket = 0
        self._charged = 0
        self._known = 0
        self._unknown = 0
        self._final_phase = False
        self._violation = False
        self.journal = Path(journal) if journal is not None else None
        if self.journal is not None:
            self.journal.parent.mkdir(parents=True, exist_ok=True)
            with self.journal.open('x', encoding='utf8'):
                pass
        self._record('budget_created', total_tokens=self.total,
                     final_tokens=self.final, request_limits=self.limits)

    def _record(self, event, **fields):
        if self.journal is None:
            return
        try:
            with self.journal.open('a', encoding='utf8') as f:
                f.write(json.dumps({'event': event, **fields}, sort_keys=True)+'\n')
                f.flush()
                os.fsync(f.fileno())
        except BaseException:
            self._violation = True  # no dispatch without a durable reservation
            raise

    def _check(self):
        if self._violation:
            raise BudgetError('Budget accounting violation: dispatch halted')

    def reserve_tokens(self, *, input_tokens, max_output_tokens, final=False):
        """Input count must include all messages/tools; output bound includes reasoning."""
        inp = _integer(input_tokens, 'input_tokens')
        out = _integer(max_output_tokens, 'max_output_tokens', 1)
        if type(final) is not bool:
            raise ValueError('final must be boolean')
        with self._lock:
            self._check()
            if final != self._final_phase:
                raise BudgetError('Request does not belong to the active budget phase')
            ceiling = self.total if final else self.total-self.final
            if self._charged+inp+out > ceiling:
                raise BudgetExceeded('Insufficient token allowance before dispatch')
            ticket = self._next_ticket
            self._record('token_reserved', ticket=ticket, input_tokens=inp,
                         max_output_tokens=out, final=final)
            self._next_ticket += 1
            self._pending[ticket] = (inp, out)
            self._charged += inp+out
            return ticket

    def settle_tokens(self, ticket, *, input_tokens=None, output_tokens=None):
        """Missing/ambiguous usage retains the upper bound, never an assumed zero."""
        with self._lock:
            if type(ticket) is not int or ticket not in self._pending:
                raise BudgetError('Unknown or already settled token reservation')
            inp, out = self._pending[ticket]
            if input_tokens is None or output_tokens is None:
                self._record('token_usage_unknown', ticket=ticket, charged=inp+out)
                self._unknown += 1
                del self._pending[ticket]
                return
            actual_in = _integer(input_tokens, 'input_tokens')
            actual_out = _integer(output_tokens, 'output_tokens')
            violation = actual_in > inp or actual_out > out
            self._record('token_settled', ticket=ticket, input_tokens=actual_in,
                         output_tokens=actual_out, violation=violation)
            self._charged += actual_in+actual_out-inp-out
            self._known += actual_in+actual_out
            del self._pending[ticket]
            if violation:
                self._violation = True
                raise BudgetError('Provider usage exceeded reserved input/output bound')

    def reserve_request(self, kind):
        """Each search attempt/page fetch (including fallback) consumes a slot."""
        with self._lock:
            self._check()
            if self._final_phase:
                raise BudgetError('No new retrieval during final answer phase')
            if kind not in self.requests:
                raise ValueError('Request kind must be search or page')
            if self.requests[kind] >= self.limits[kind]:
                raise BudgetExceeded(f'{kind} request allowance exhausted')
            self._record('request_reserved', kind=kind, attempt=self.requests[kind]+1)
            self.requests[kind] += 1

    def begin_final(self):
        with self._lock:
            self._check()
            if self._pending:
                raise BudgetError('Settle all in-flight model attempts before final answer')
            if self._final_phase:
                raise BudgetError('Final phase already started')
            self._record('final_phase_started')
            self._final_phase = True

    def snapshot(self):
        with self._lock:
            return {'charged_tokens': self._charged, 'known_actual_tokens': self._known,
                    'unknown_usage_attempts': self._unknown,
                    'pending_attempts': len(self._pending),
                    'requests': dict(self.requests), 'violation': self._violation,
                    'final_phase': self._final_phase}
