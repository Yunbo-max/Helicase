"""Strict application of model-proposed quote repairs, with a complete change log."""
from copy import deepcopy
from .evaluation import validate_extraction


def invalid_quote_targets(graph, report):
    targets=[];seen=set()
    for kind in ('nodes','edges'):
        if not isinstance(graph.get(kind),list):raise ValueError('Missing graph arrays')
        for row in graph[kind]:
            key=(kind,row.get('id'))
            if not row.get('id') or key in seen:raise ValueError('Missing or duplicate graph ID')
            seen.add(key);quote=row.get('quote')
            if not isinstance(quote,str) or not quote.strip() or quote not in report:
                targets.append({**row,'kind':kind})
    return targets


def apply_quote_patches(graph, report, patches):
    targets={(r['kind'],r['id']) for r in invalid_quote_targets(graph,report)}
    if not isinstance(patches,list):raise ValueError('Repairs must be an array')
    proposed={}
    for p in patches:
        key=(p.get('kind'),p.get('id'))
        if key in proposed:raise ValueError('Duplicate quote repair')
        quote=p.get('quote')
        if 'quote' not in p or (quote is not None and
            (not isinstance(quote,str) or not quote.strip() or quote not in report)):
            raise ValueError('Repair quote must be literal report text or explicit null')
        if not isinstance(p.get('reason'),str) or not p['reason'].strip():raise ValueError('Repair reason required')
        proposed[key]=p
    if set(proposed)!=targets:raise ValueError('Repairs must cover exactly the invalid-quote items')
    obj=deepcopy(graph);changes=[];removed_nodes=set()
    for kind in ('nodes','edges'):
        kept=[]
        for row in obj[kind]:
            p=proposed.get((kind,row['id']))
            if p is not None:
                entry={'kind':kind,'id':row['id'],'original_item':deepcopy(row),'reason':p['reason']}
                if p['quote'] is None:
                    changes.append(dict(entry,action='remove_unsupported_item'))
                    if kind=='nodes':removed_nodes.add(row['id'])
                    continue
                row['quote']=p['quote']
                changes.append(dict(entry,action='replace_quote',literal_report_quote=p['quote']))
            kept.append(row)
        obj[kind]=kept
    for edge in obj['edges']:
        if edge.get('source_id') in removed_nodes or edge.get('target_id') in removed_nodes:
            raise ValueError('Unsupported node would remove an unreviewed edge; structural review required')
    return validate_extraction(obj,report),changes
