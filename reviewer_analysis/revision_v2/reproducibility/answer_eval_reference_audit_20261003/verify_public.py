"""Offline arithmetic and published-artifact integrity checks; no model calls."""
import csv
import hashlib
import json
import math
from pathlib import Path
from collections import defaultdict

P = Path(__file__).resolve().parent
METHODS = {'Helicase','Claude','DeepSeek','GLM','Qwen3-235B','ReAct','ToT'}
QUERIES = {f'Q{i}' for i in range(61,81)}
METRICS = ['answer_precision','answer_recall','answer_f1','legacy_composite']
def close(a,b):
    assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-12), (a,b)
def read(name):return json.loads((P/name).read_text())
def check_rows(name, new=False):
    rows=list(csv.DictReader((P/name).open()))
    groups=defaultdict(list)
    for r in rows:
        groups[r.get('judge','legacy')].append(r)
        p,rec,a,comp=(float(r[k]) for k in METRICS)
        v,e=int(r['native_nodes']),int(r['native_edges'])
        close(a,2*p*rec/(p+rec) if p+rec else 0)
        if new:
            np,nr,m=(int(r[k]) for k in ['n_pred_units','n_reference_units','matched_units'])
            assert nr>0 and 0<=m<=min(np,nr)
            close(p,m/np if np else 0);close(rec,m/nr)
        factor=.8+.2*min(1,e/v) if v and e else .85
        rp=(a if v and e else p)*factor;rr=rec*factor
        rf=2*rp*rr/(rp+rr) if rp+rr else 0
        close(r['relation_proxy_f1'],rf);close(comp,.6*a+.4*rf)
        close(r['structure_delta'],comp-a)
    for rs in groups.values():
        assert len(rs)==140 and {(r['method'],r['query_id']) for r in rs}=={(m,q) for m in METHODS for q in QUERIES}
    if new:
        assert set(groups)=={'gpt-5.5','gpt-5.6-sol'}
        assert all(sum(int(r['n_pred_units']) for r in rs)==517 for rs in groups.values())
    return rows

def check_summary(rows, summary):
    for s in summary:
        rs=[r for r in rows if r['method']==s['method']]
        for k in METRICS:close(s[k],sum(float(r[k]) for r in rs)/len(rs))

for label in ['legacy_scpqa','legacy_gt_q4']:
    rows=check_rows(label+'_per_query.csv')
    check_summary(rows,read(label+'_summary.json')['summary'])
for label in ['raw','reviewed']:
    rows=check_rows('new_gt_q4_'+label+'_per_query.csv',new=True)
    check_summary(rows,read('new_gt_q4_'+label+'_summary.json')['summary'])
for line in (P/'SHA256SUMS').read_text().splitlines():
    expected,name=line.split('  ',1)
    assert hashlib.sha256((P/name).read_bytes()).hexdigest()==expected, name
print('Verified 840 published score rows, all macro means, formulas, universes and artifact hashes. Semantic validity is not established by these checks.')
