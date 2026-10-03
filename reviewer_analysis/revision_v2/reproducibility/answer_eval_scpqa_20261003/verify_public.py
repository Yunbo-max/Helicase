"""Offline verification of fixed-prediction scpqa matching scores, no model calls."""
import csv, hashlib, json, math, statistics
from pathlib import Path
p=Path(__file__).resolve().parent
rows=list(csv.DictReader((p/'per_query_scores.csv').open()))
summary=json.loads((p/'summary.json').read_text())
methods={'Helicase','Claude','DeepSeek','GLM','Qwen3-235B','ReAct','ToT'}
judges={'gpt-5.5','gpt-5.6-sol'}
queries={f'Q{i}' for i in range(61,81)}
assert len(rows)==280
assert {(r['method'],r['query_id'],r['judge']) for r in rows}=={(m,q,j) for m in methods for q in queries for j in judges}
for r in rows:
    np,nr,m=(int(r[k]) for k in ['n_pred_units','n_reference_units','matched_units'])
    assert nr>0 and 0<=m<=min(np,nr)
    expected={'answer_precision':m/np if np else 0,'answer_recall':m/nr,'answer_f1':2*m/(np+nr)}
    for k,v in expected.items():assert math.isclose(float(r[k]),v,abs_tol=1e-12)
for s in summary['summary']:
    rs=[r for r in rows if r['method']==s['method']]
    for metric in ['answer_precision','answer_recall','answer_f1']:
        assert math.isclose(statistics.mean(float(r[metric]) for r in rs),s[metric],abs_tol=1e-12)
        for j in judges:
            v=statistics.mean(float(r[metric]) for r in rs if r['judge']==j)
            assert math.isclose(v,s[metric+'_judge_means'][j],abs_tol=1e-12)
for j in judges:
    assert sum(int(r['n_pred_units']) for r in rows if r['judge']==j)==517
for q in queries:
    assert len({r['n_reference_units'] for r in rows if r['query_id']==q})==1
for line in (p/'SHA256SUMS').read_text().splitlines():
    expected,name=line.split('  ',1)
    assert hashlib.sha256((p/name).read_bytes()).hexdigest()==expected,name
print('Verified 280 unique score rows, 517 fixed predictions per judge, reference counts, P/R/F1 formulas, judge means, macro means and artifact hashes. Semantic validity is a separate question.')
