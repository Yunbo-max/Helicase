"""Recompute legacy arithmetic/paired intervals from public counts; no models or keys."""
import csv,hashlib,json,math,random,statistics
from pathlib import Path
p=Path(__file__).resolve().parent
summary=json.loads((p/'summary.json').read_text())
manifest=json.loads((p/'manifest.json').read_text())
for name,wanted in manifest['public_file_sha256'].items():
    assert hashlib.sha256((p/name).read_bytes()).hexdigest()==wanted,name
rows=list(csv.DictReader((p/'per_execution.csv').open()))
metrics=['answer_precision','answer_recall','answer_f1','relation_proxy_f1','legacy_composite','structure_delta']
expected={(f'Q{q}',m,str(r)) for q in range(61,81) for m in ['full','uniform'] for r in [1,2]}
assert len(rows)==80 and {(r['query_id'],r['method'],r['repeat']) for r in rows}==expected
h=lambda x,y:2*x*y/(x+y) if x+y else 0
close=lambda a,b:math.isclose(float(a),float(b),abs_tol=1e-12)
for r in rows:
    np,nr=int(r['predicted_items']),int(r['reference_items'])
    ep=int(r['matched_prediction_strings'])/np if np else 0
    er=int(r['matched_reference_strings'])/nr if nr else 0
    a=h(ep,er);v,e=int(r['native_nodes']),int(r['native_edges'])
    factor=.8+.2*min(1,e/v) if v and e else None
    rp,rr=(a*factor,er*factor) if factor is not None else (.85*ep,.85*er)
    rel=h(rp,rr);total=.6*a+.4*rel
    for metric,value in zip(metrics,[ep,er,a,rel,total,total-a]):assert close(r[metric],value),(r['run_id'],metric)
for m in ['full','uniform']:
    rs=[r for r in rows if r['method']==m]
    for metric in metrics:assert close(statistics.mean(float(r[metric]) for r in rs),summary['methods'][m][metric])
    for metric in ['answer_f1','legacy_composite']:
        means=[statistics.mean(float(r[metric]) for r in rs if r['repeat']==str(rep)) for rep in [1,2]]
        assert all(close(a,b) for a,b in zip(means,summary['methods'][m][metric+'_repeat_means']))
        assert close(statistics.stdev(means),summary['methods'][m][metric+'_repeat_sample_sd'])
qrows=list(csv.DictReader((p/'per_query.csv').open()))
assert len(qrows)==20 and {r['query_id'] for r in qrows}=={f'Q{q}' for q in range(61,81)}
for qr in qrows:
    for m in ['full','uniform']:
        rs=[r for r in rows if r['query_id']==qr['query_id'] and r['method']==m]
        for metric in metrics:assert close(qr[m+'_'+metric],statistics.mean(float(r[metric]) for r in rs))
for metric in ['answer_f1','legacy_composite']:
    d=[]
    for q in range(61,81):
        qr=next(r for r in qrows if r['query_id']==f'Q{q}')
        delta=float(qr['full_'+metric])-float(qr['uniform_'+metric])
        assert close(qr[metric+'_difference'],delta);d.append(delta)
    check=summary['paired'][metric];assert close(statistics.mean(d),check['difference'])
    rng=random.Random(check['seed'])
    boot=sorted(math.fsum(d[int(rng.random()*20)] for _ in range(20))/20 for _ in range(check['n_boot']))
    def quantile(t):
        pos=(len(boot)-1)*t;i=int(pos)
        return boot[i]+(pos-i)*(boot[min(i+1,len(boot)-1)]-boot[i])
    assert all(close(x,y) for x,y in zip([quantile(.025),quantile(.975)],check['ci95']))
print(json.dumps({'executions':80,'queries':20,'formula_macro_repeat_statistics_bootstrap_hashes_verified':True,'scope':'Public count arithmetic only; raw semantic judgments and full usage require retained private traces.'}))
