"""Exact original-text selection from model-selected, one-based line ranges."""


def select_report_lines(report, start, end):
    lines = report.splitlines(keepends=True)
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
        raise ValueError('Selection must identify an existing contiguous one-based line range')
    quote = ''.join(lines[start - 1:end])
    if not quote.strip():
        raise ValueError('Selection contains no evidence text')
    assert quote in report
    return quote
