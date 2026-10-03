"""Complete-case Q4 answer and legacy-composite statistics; no model calls."""
import argparse
import csv
import itertools
import json
from pathlib import Path
import numpy as np
from .metrics import paired_query_statistics
from .answer_units import score_answer, digest, write_json

METHODS=['Helicase','Claude','DeepSeek','GLM','Qwen3-235B','ReAct','ToT']
QUERIES=[f'Q{i}' for i in range(61,81)]
METRICS=['answer_precision','answer_recall','answer_f1','legacy_composite']
WEIGHTS=[0,.25,.4,.5]
SEED=20261003


def analyse(rows,n_boot=10000):
    keys=[(r['method'],r['query_id']) for r in rows]
    if len(keys)!=len(set(keys)) or set(keys)!=set(itertools.product(METHODS,QUERIES)):
        raise ValueError('Require exactly one complete result for all seven methods and twenty queries')
    for r in rows:
        if not r.get('input_hash'):raise ValueError('Missing frozen input hash')
        p,n,m=r['n_pred_units'],r['n_reference_units'],r['matched_units']
        if any(type(v)!=int or v<0 for v in [p,n,m]) or not n or m>min(p,n):raise ValueError('Invalid matching counts')
        expected=score_answer(list(range(p)),list(range(n)),[[i,i] for i in range(m)],r['native_nodes'],r['native_edges'])
        for metric in METRICS+['relation_proxy_f1','structure_delta']:
            if not np.isfinite(r[metric]) or abs(r[metric]-expected[metric])>1e-12:raise ValueError('Count/formula inconsistency')
    rng=np.random.default_rng(SEED);indices=rng.integers(20,size=(n_boot,20));summary=[]
    for method in METHODS:
        data=sorted([r for r in rows if r['method']==method],key=lambda r:int(r['query_id'][1:]))
        item={'method':method,'n_queries':len(data),'n_abstentions':sum(r['n_pred_units']==0 for r in data),
              'mean_structure_delta':float(np.mean([r['structure_delta'] for r in data])),
              'total_predicted_units':sum(r['n_pred_units'] for r in data),
              'total_reference_units':sum(r['n_reference_units'] for r in data),
              'total_matched_units':sum(r['matched_units'] for r in data)}
        for metric in METRICS:
            values=np.array([r[metric] for r in data]);item[metric]=float(values.mean())
            item[metric+'_95ci']=np.quantile(values[indices].mean(axis=1),[.025,.975]).tolist()
        summary.append(item)
    paired=[paired_query_statistics(rows,a,b,metric=metric,n_boot=n_boot,seed=SEED,expected_query_ids=QUERIES)
            for a,b in itertools.combinations(METHODS,2) for metric in METRICS]
    weights=[];weight_pairs=[];weight_summary=[]
    for weight in WEIGHTS:
        weighted=[dict(r,structure_weight=weight,weighted_composite=(1-weight)*r['answer_f1']+weight*r['relation_proxy_f1']) for r in rows]
        weights.extend({k:r[k] for k in ['method','run_id','query_id','structure_weight','answer_f1','relation_proxy_f1','weighted_composite']} for r in weighted)
        for a,b in itertools.combinations(METHODS,2):
            value=paired_query_statistics(weighted,a,b,metric='weighted_composite',n_boot=n_boot,seed=SEED,expected_query_ids=QUERIES)
            weight_pairs.append(dict(value,structure_weight=weight))
        weight_summary.extend({'method':m,'structure_weight':weight,'mean':float(np.mean([r['weighted_composite'] for r in weighted if r['method']==m]))} for m in METHODS)
    return {'summary':summary,'paired':paired,'weight_rows':weights,'weight_pairs':weight_pairs,'weight_summary':weight_summary,
            'protocol':{'query_ids':QUERIES,'methods':METHODS,'n_boot':n_boot,'seed':SEED,'weights':WEIGHTS,
                'input_scores_sha256':digest(rows),'reference_status':'AI normalized prose reference; independent human review pending',
                'estimand':'Macro-average across the fixed 20 Q4 queries from one archived run per method.',
                'confidence_intervals':'Pointwise query bootstrap percentile 95% intervals; not family-wise multiplicity adjusted.',
                'limitations':'Not independent agent runs, not matched-budget causal evidence, not open-world factual truth.'}}


def write_csv(path,rows):
    with Path(path).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--scores',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--historical');args=ap.parse_args()
    rows=json.loads(Path(args.scores).read_text());result=analyse(rows);out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    write_json(out/'statistics.json',result)
    write_csv(out/'summary.csv',result['summary']);write_csv(out/'weight_sensitivity.csv',result['weight_rows'])
    simple=[{k:r[k] for k in ['method','run_id','query_id',*METRICS,'relation_proxy_f1','structure_delta','native_nodes','native_edges','n_pred_units','n_reference_units','matched_units','input_hash','evaluator_version']} for r in rows]
    write_csv(out/'per_query_scores.csv',simple)
    if args.historical:
        with Path(args.historical).open() as f:old={(r['method'],r['query_id']):r for r in csv.DictReader(f)}
        joined=[]
        for r in rows:
            previous=old[(r['method'],r['query_id'])]
            joined.append({'method':r['method'],'query_id':r['query_id'],'historical_answer_component':previous['historical_A'],
                'historical_reported_composite':previous['historical_L'],'historical_counts_in_range':previous['historical_counts_in_range'],
                'new_answer_f1':r['answer_f1'],'recomputed_legacy_composite':r['legacy_composite'],
                'comparison_caveat':'Different answer-unit protocol; historic judge pairs unavailable; not a controlled single-change experiment.'})
        write_csv(out/'historical_vs_new.csv',joined)
    lines=['# Q4 答案项与旧复合分重算统计','',
      '这是原存档报告的新版答案项评估，参考单位经 AI 规范化；独立人工核验尚未完成。历史值保留，未重新命名为新的答案 F1。','',
      '| 方法 | 答案 P | 答案 R | 答案 F1 | 旧公式重算 L | 结构调整 L−A |','|---|---:|---:|---:|---:|---:|']
    for r in result['summary']:
        lines.append('| '+r['method']+' | '+' | '.join(f"{r[k]:.4f}" for k in [*METRICS,'mean_structure_delta'])+' |')
    lines.extend(['','全部七方法均覆盖 Q61–Q80，无失败题静默删除。置信区间按问题重采样 10,000 次，固定种子 20261003；四项指标均报告全部 21 对方法比较。',
      '结构权重 0、0.25、0.4、0.5 均计算全部问题及全部方法对；结果见 statistics.json 和 weight_sensitivity.csv。',
      '区间为逐项区间，未做多重比较校正。只有一个历史 run，不代表独立运行方差或严格预算匹配效果。',
      '参考外答案只表示未匹配，不能自动判为事实错误。本文指标也不能代替具体引用证据支持率。'])
    (out/'RESULTS_ZH.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'rows':len(rows),'methods':len(result['summary']),'paired_comparisons':len(result['paired']),'out':str(out)}))


if __name__=='__main__':main()
