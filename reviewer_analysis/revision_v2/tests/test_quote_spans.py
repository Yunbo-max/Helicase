import pytest
from reviewer_analysis.revision_v2.quote_spans import select_report_lines


def test_exact_lines_keep_markdown_and_newlines():
    report = 'Heading\n**A** supplies B.\nScope limited.\n'
    assert select_report_lines(report, 2, 3) == '**A** supplies B.\nScope limited.\n'


@pytest.mark.parametrize('start,end', [(0, 1), (2, 1), (1, 4), (True, 1), (1.0, 1), (None, 1)])
def test_invalid_line_range_rejected(start, end):
    with pytest.raises(ValueError):
        select_report_lines('one\ntwo\n', start, end)


def test_blank_only_selection_rejected():
    with pytest.raises(ValueError):
        select_report_lines('one\n\n', 2, 2)
