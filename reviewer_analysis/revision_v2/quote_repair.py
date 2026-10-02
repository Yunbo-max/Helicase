"""Auditable whitespace-only quotation recovery, separate from first-pass results."""
from copy import deepcopy
import re
from .evaluation import validate_extraction


def recover_quote(quote, report):
    """Return a unique literal span; never change words, punctuation or case."""
    if not isinstance(quote,str) or not quote.strip():return None
    if quote in report:return quote
    wanted=re.sub(r'\s+',' ',quote.strip())
    tokens=list(re.finditer(r'\s+|\S',report))
    normalized=''.join(' ' if m.group().isspace() else m.group() for m in tokens)
    start=normalized.find(wanted)
    if start<0 or normalized.find(wanted,start+1)>=0:return None
    return report[tokens[start].start():tokens[start+len(wanted)-1].end()]


def repair_graph_quotes(graph, report):
    """Preserve assertions and log every quote change, then run the strict validator."""
    obj=deepcopy(graph);changes=[]
    for field in ('nodes','edges'):
        if not isinstance(obj.get(field),list):raise ValueError('Missing graph arrays')
        for row in obj[field]:
            old=row.get('quote');new=recover_quote(old,report)
            if new is None:raise ValueError(f'Quote not uniquely recoverable by whitespace: {field}/{row.get("id")}')
            if new!=old:
                changes.append({'field':field,'id':row.get('id'),'old_quote':old,'literal_report_quote':new})
                row['quote']=new
    return validate_extraction(obj,report),changes
