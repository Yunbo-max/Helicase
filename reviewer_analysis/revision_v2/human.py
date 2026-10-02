"""Blinded sampling, blank rating forms and pre-adjudication agreement."""
from __future__ import annotations
import csv
import random
from collections import Counter,defaultdict
from pathlib import Path
from .common import new_directory, unique_index, write_json, write_jsonl

STATES={'supported','contradicted','unresolved'}
CITATION_STATES={'entails','contradicts','not_enough_evidence','unavailable'}


def make_forms(facts,out,sample=400,seed=268226721,required_queries=('Q61','Q64')):
    if sample<=0:raise ValueError('sample must be positive')
    pool=[f for f in facts if f['quadrant']=='Q4' and f['fact_type']=='edge']
    unique_index(pool,'fact_id')
    rng=random.Random(seed);required=[f for f in pool if f['query_id'] in required_queries]
    if len(required)>sample:raise ValueError(f'Required case edges ({len(required)}) exceed sample. Increase --sample.')
    ids={f['fact_id'] for f in required};groups=defaultdict(list)
    for f in pool:
        if f['fact_id'] not in ids:
            c=f.get('confidence');bucket='missing' if c is None else min(4,int(c*5))
            groups[(f['method'],f['quadrant'],str(bucket))].append(f)
    for g in groups.values():rng.shuffle(g)
    selected=list(required)
    while len(selected)<sample and any(groups.values()):
        keys=list(groups);rng.shuffle(keys)
        for k in keys:
            if groups[k] and len(selected)<sample:selected.append(groups[k].pop())
    rng.shuffle(selected);out=new_directory(out);key=[];forms=[]
    for i,f in enumerate(selected,1):
        iid=f'I{i:04d}';key.append({'item_id':iid,'fact_id':f['fact_id']})
        forms.append({'item_id':iid,'question':f['question'],'claim':f['claim'],
            'scope':str(f.get('scope',{})),'citation_urls':'\n'.join(f['citation_urls']),
            'truth_status':'','citation_status':'','evidence_type':'','validity_scope':'',
            'supporting_quote':'','notes':''})
    for name in ('rater_a.csv','rater_b.csv'):
        with (out/name).open('w',newline='',encoding='utf-8-sig') as fh:
            writer=csv.DictWriter(fh,fieldnames=list(forms[0]) if forms else ['item_id','truth_status','citation_status'])
            writer.writeheader();writer.writerows(forms)
    write_jsonl(out/'PRIVATE_mapping.jsonl',key)
    write_json(out/'sampling.json',{'seed':seed,'n_requested':sample,'n_sampled':len(selected),
        'n_population':len(pool),'required_queries':list(required_queries),
        'sampling':'Case census plus round-robin method/confidence strata; not a simple random sample.',
        'limits':'Report case and stratified audit results separately. Do not use unweighted enriched samples as population-wide calibration.'})
    return len(selected)


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def agreement(a,b):
    aa=unique_index(a,'item_id');bb=unique_index(b,'item_id');out={}
    for field,allowed in [('truth_status',STATES),('citation_status',CITATION_STATES)]:
        for row in list(aa.values())+list(bb.values()):
            if row.get(field,'') not in allowed|{''}:raise ValueError(f'Invalid {field} label')
        pairs=[(aa[k].get(field),bb[k].get(field)) for k in sorted(aa.keys()&bb.keys())
               if aa[k].get(field) and bb[k].get(field)]
        n=len(pairs);p=sum(x==y for x,y in pairs)/n if n else None
        ca=Counter(x for x,y in pairs);cb=Counter(y for x,y in pairs)
        expected=sum(ca[k]*cb[k] for k in ca)/(n*n) if n else None
        kappa=(p-expected)/(1-expected) if n and expected<1 else None
        out[field]={'n_paired':n,'raw_agreement':p,'cohen_kappa':kappa,
            'disagreements':[k for k in aa.keys()&bb.keys() if aa[k].get(field) and bb[k].get(field) and aa[k][field]!=bb[k][field]],
            'missing_or_unpaired':len(aa.keys()|bb.keys())-n}
    out['note']='Calculated from original independent ratings before adjudication. Unresolved is a category, not false.'
    return out


def ratings_to_labels(ratings,mapping,assessor):
    mapping=unique_index(mapping,'item_id');unique_index(ratings,'item_id');result=[]
    for r in ratings:
        if r['item_id'] not in mapping:raise ValueError('Rating not in blinded mapping')
        s=r.get('truth_status','')
        if not s:continue  # Blank means unlabelled, not unresolved and not false.
        if s not in STATES:raise ValueError('Invalid truth label')
        result.append({'fact_id':mapping[r['item_id']]['fact_id'],'assessor':assessor,'assessor_type':'human',
                       'truth_status':s,'citation_status':r.get('citation_status'),
                       'notes':r.get('notes'),'supporting_quote':r.get('supporting_quote'),
                       'validity_scope':r.get('validity_scope'),'sample_design':'enriched_stratified_audit'})
    return result
