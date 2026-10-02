"""Strict fact-level metrics and explicit one-to-one graph-match scoring."""
from __future__ import annotations
from collections import defaultdict
from urllib.parse import urlparse
import numpy as np
from .common import unique_index


def _bins(c, y, edges):
    ids=np.searchsorted(edges[1:-1],c,side='right')
    bins=[]
    for b in np.unique(ids):
        use=ids==b
        bins.append({'left':float(edges[b]),'right':float(edges[b+1]),'n':int(use.sum()),
                     'confidence':float(c[use].mean()),'accuracy':float(y[use].mean())})
    return bins


def calibration(confidences, labels, n_bins=10):
    c=np.asarray(confidences,dtype=float); y=np.asarray(labels,dtype=float)
    if c.ndim!=1 or len(c)==0 or c.shape!=y.shape: raise ValueError('Expected aligned nonempty 1D arrays')
    if not np.all(np.isfinite(c)) or np.any((c<0)|(c>1)): raise ValueError('Invalid confidence; scores are never clipped')
    if not np.all(np.isin(y,[0,1])): raise ValueError('Labels must be binary on the assessed subset')
    if n_bins<1: raise ValueError('n_bins must be positive')
    fixed=_bins(c,y,np.linspace(0,1,n_bins+1))
    # Unique quantile edges prevent arbitrary splitting of tied confidence values.
    interior=np.unique(np.quantile(c,np.arange(1,n_bins)/n_bins))
    interior=interior[(interior>c.min())&(interior<c.max())]
    adaptive=_bins(c,y,np.r_[0,interior,1])
    def ece(bs): return sum(b['n']*abs(b['accuracy']-b['confidence']) for b in bs)/len(c)
    return {'n':len(c),'brier':float(np.mean((c-y)**2)),'ece':ece(fixed),
            'adaptive_ece':ece(adaptive),'mean_gap':float(abs(c.mean()-y.mean())),
            'mean_confidence':float(c.mean()),'accuracy':float(y.mean()),
            'bins':fixed,'adaptive_bins':adaptive}


def _cluster_ci(rows, n_boot, seed):
    grouped=defaultdict(list)
    for r in rows: grouped[r['query_id']].append(r)
    ids=sorted(grouped)
    if len(ids)<2 or n_boot<2: return None
    rng=np.random.default_rng(seed); vals=[]
    for _ in range(n_boot):
        sample=[r for i in rng.integers(len(ids),size=len(ids)) for r in grouped[ids[i]]]
        out=calibration([r['confidence'] for r in sample],[r['label'] for r in sample])
        vals.append([out['brier'],out['ece'],out['adaptive_ece']])
    lo,hi=np.quantile(vals,[.025,.975],axis=0)
    return {k:[float(lo[i]),float(hi[i])] for i,k in enumerate(['brier','ece','adaptive_ece'])}


def analyse_labels(facts, labels, n_boot=2000, seed=268226721):
    if not facts or not labels: raise ValueError('Nonempty fact records and actual labels are required')
    lookup=unique_index(facts,'fact_id'); known=set(); groups=defaultdict(dict)
    for y in labels:
        if y['fact_id'] not in lookup: raise ValueError('Label does not identify an input fact')
        if y.get('truth_status') not in ('supported','contradicted','unresolved'):
            raise ValueError('Explicit truth_status required; unmatched reference is not false')
        if not y.get('assessor') or y.get('assessor_type') not in ('llm','human'):
            raise ValueError('Explicit assessor and assessor_type required')
        k=(y['assessor'],y['assessor_type'])
        if (k,y['fact_id']) in known: raise ValueError('Duplicate fact label for one assessor')
        known.add((k,y['fact_id'])); groups[k][y['fact_id']]=y
    result=[]
    for (assessor,kind), lab in sorted(groups.items()):
        strata=defaultdict(list)
        for f in facts: strata[(f['method'],f['fact_type'])].append(f)
        for (method,fact_type), fs in sorted(strata.items()):
            cs=[f for f in fs if f.get('confidence') is not None]
            for f in cs:
                c=f['confidence']
                if not np.isfinite(c) or not 0<=c<=1: raise ValueError(f'Invalid score in fact {f["fact_id"]}')
            # A method with no labels from this judge is retained as missing coverage.
            binary=[]; unresolved=0; missing=0; low=0.;high=0.
            for f in cs:
                y=lab.get(f['fact_id']); c=f['confidence']
                if y and y['truth_status']!='unresolved':
                    value=int(y['truth_status']=='supported')
                    binary.append(dict(f,label=value))
                    low+=(c-value)**2;high+=(c-value)**2
                else:
                    unresolved+=int(y is not None);missing+=int(y is None)
                    low+=min(c*c,(1-c)**2);high+=max(c*c,(1-c)**2)
            metric=calibration([f['confidence'] for f in binary],[f['label'] for f in binary]) if binary else None
            baseline={}
            if binary:
                baseline['constant_0.5']=calibration([.5]*len(binary),[f['label'] for f in binary])['brier']
                domains=[len({urlparse(u).hostname for u in f.get('citation_urls',[])}) for f in binary]
                baseline['domain_count_k_over_k_plus_1']=calibration([k/(k+1) for k in domains],[f['label'] for f in binary])['brier']
            result.append({'method':method,'fact_type':fact_type,'assessor':assessor,'assessor_type':kind,
                'n_facts':len(fs),'n_with_confidence':len(cs),'n_without_confidence':len(fs)-len(cs),
                'n_labelled_binary':len(binary),'n_unresolved':unresolved,'n_missing_labels':missing,
                'label_coverage':len(binary)/len(cs) if cs else None,
                'n_queries_assessed':len({f['query_id'] for f in binary}),
                'metrics':metric,'query_cluster_bootstrap_95ci':_cluster_ci(binary,n_boot,seed),
                'brier_all_fact_bounds':[low/len(cs),high/len(cs)] if cs else None,
                'simple_baseline_brier':baseline})
    return {'estimand':'Micro-average over binary-assessed facts; CI clusters queries and retains all runs within a query.',
            'warning':'Unresolved/missing labels are not false. Bounds are algebraic extremes, not CIs. LLM labels are not human ground truth. Domains do not establish independent sources.',
            'groups':result,'n_boot':n_boot,'seed':seed}


def _graph(g):
    nodes=g.get('nodes',[]);edges=g.get('edges',[])
    if isinstance(nodes,dict): nodes=[dict(v,id=str(v.get('id',k))) for k,v in nodes.items()]
    if isinstance(edges,dict): edges=[dict(v,id=str(v.get('id',k))) for k,v in edges.items()]
    nodes=unique_index(nodes,'id'); edges=unique_index(edges,'id')
    seen=set()
    for e in edges.values():
        if e.get('source_id') not in nodes or e.get('target_id') not in nodes: raise ValueError('Dangling graph endpoint')
        key=(e['source_id'],e.get('relation_type'),e['target_id'])
        if key in seen: raise ValueError('Duplicate typed triple; canonicalise and preserve its alias map before scoring')
        seen.add(key)
    return nodes,edges


def _pairs(pairs, pred, gold):
    left=set();right=set();out={}
    for pair in pairs:
        if len(pair)!=2: raise ValueError('Matching pairs must have exactly two IDs')
        a,b=pair
        if a not in pred or b not in gold: raise ValueError('Unknown matched record ID')
        if a in left or b in right: raise ValueError('Matching must be one-to-one; counts are never clipped')
        left.add(a);right.add(b);out[a]=b
    return out


def _f1(tp,npred,ngold):
    return 2*tp/(npred+ngold) if npred+ngold else None


def score_graph(pred, gold, node_matches, edge_matches):
    pn,pe=_graph(pred);gn,ge=_graph(gold)
    nm=_pairs(node_matches,pn,gn);em=_pairs(edge_matches,pe,ge)
    for a,b in em.items():
        p,g=pe[a],ge[b]
        if nm.get(p['source_id'])!=g['source_id'] or nm.get(p['target_id'])!=g['target_id']:
            raise ValueError('Relation match contradicts directed endpoint mapping')
        # Relation semantic equivalence is an explicit input judgment, not inferred here.
    ef=_f1(len(nm),len(pn),len(gn));rf=_f1(len(em),len(pe),len(ge))
    return {'n_pred_nodes':len(pn),'n_reference_nodes':len(gn),'matched_nodes':len(nm),
            'n_pred_edges':len(pe),'n_reference_edges':len(ge),'matched_edges':len(em),
            'entity_precision':len(nm)/len(pn) if pn else 0.,'entity_recall':len(nm)/len(gn) if gn else None,
            'relation_precision':len(em)/len(pe) if pe else 0.,'relation_recall':len(em)/len(ge) if ge else None,
            'entity_f1':ef,'relation_f1':rf,'graph_f1':.6*ef+.4*rf if ef is not None and rf is not None else None,
            'node_matches':node_matches,'edge_matches':edge_matches,
            'interpretation':'Closed-reference matching, not open-world factual truth. Relation type equivalence must be adjudicated in the supplied pairs.'}


def paired_query_statistics(rows, method_a, method_b, metric='graph_f1', n_boot=10000, seed=268226721, expected_query_ids=None):
    """Compare query means. Do not treat repeated runs as independent queries."""
    grouped=defaultdict(list)
    for r in rows:
        v=r.get(metric)
        if r.get('method') in (method_a,method_b):
            if v is None: raise ValueError('Missing metric in a declared query; do not silently exclude incomplete evaluations')
            if not np.isfinite(v) or not 0<=v<=1: raise ValueError('Invalid performance metric')
            grouped[(r['method'],r['query_id'])].append(float(v))
    qa={q for m,q in grouped if m==method_a};qb={q for m,q in grouped if m==method_b}
    if expected_query_ids is not None and (qa!=set(expected_query_ids) or qb!=set(expected_query_ids)):
        raise ValueError('Evaluated query set does not match the declared protocol')
    if qa!=qb: raise ValueError('Paired query sets differ; missing/failed runs must be resolved or reported, not silently dropped')
    if len(qa)<2: raise ValueError('At least two paired queries required')
    qs=sorted(qa); a=np.array([np.mean(grouped[(method_a,q)]) for q in qs]);b=np.array([np.mean(grouped[(method_b,q)]) for q in qs]);d=a-b
    rng=np.random.default_rng(seed)
    samples=d[rng.integers(len(qs),size=(n_boot,len(qs)))].mean(axis=1)
    return {'method_a':method_a,'method_b':method_b,'metric':metric,'n_queries':len(qs),
            'mean_difference':float(d.mean()),'query_bootstrap_95ci':np.quantile(samples,[.025,.975]).tolist(),
            'wins':int((d>0).sum()),'ties':int((d==0).sum()),'losses':int((d<0).sum()),
            'runs_per_query':{q:{m:len(grouped[(m,q)]) for m in (method_a,method_b)} for q in qs},
            'estimand':'Mean of query-level differences after averaging available runs per method; not a matched-budget causal effect.'}
