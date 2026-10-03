"""Three-model frozen-sample diagnostics; no model calls or relabelling."""
from collections import Counter
from itertools import combinations
import csv
import json
from pathlib import Path
import sys

R = Path(__file__).resolve().parent
sys.path.insert(0, str(R))
from analyse_secondary import audit as audit_secondary, agreement, paired_calibration, sha
from audit_tertiary import audit as audit_tertiary
from reviewer_analysis.revision_v2.common import write_json, write_jsonl, utcnow
from reviewer_analysis.revision_v2.metrics import analyse_labels

OUT = R / 'diversity_comparison_v1'
MODELS = ['gpt-5.5', 'gpt-5.6-sol', 'gpt-5.6-terra']
CLASSES = ('supported', 'contradicted', 'unresolved')


def pattern_summary(ids, labels, models):
    if len(ids) != len(set(ids)) or len(models) != len(set(models)) or len(models) != 3:
        raise ValueError('Unique fact IDs and exactly three distinct models required')
    counts = Counter()
    for fid in ids:
        if any(fid not in labels.get(m, {}) for m in models):
            raise ValueError('All models must label every selected fact')
        pattern = tuple(labels[m][fid]['truth_status'] for m in models)
        if any(s not in CLASSES for s in pattern):
            raise ValueError('Invalid truth status')
        counts[pattern] += 1
    unanimous = sum(n for p, n in counts.items() if len(set(p)) == 1)
    two = sum(n for p, n in counts.items() if len(set(p)) == 2)
    distinct = sum(n for p, n in counts.items() if len(set(p)) == 3)
    return {'n': len(ids), 'model_order': models, 'unanimous': unanimous, 'two_agree': two,
            'all_different': distinct, 'any_disagreement': two + distinct,
            'unanimous_fraction': unanimous / len(ids) if ids else None,
            'patterns': [{'labels': dict(zip(models, p)), 'n': n} for p, n in sorted(counts.items())]}


def main():
    facts, primary, secondary, called, mechanical, old_audit = audit_secondary()
    tfacts, tprimary, tertiary, tcalled, tmechanical, new_audit = audit_tertiary()
    assert facts == tfacts and primary == tprimary and called == tcalled and mechanical == tmechanical
    prior = json.loads((R / 'diversity_prior_sha256.json').read_text())
    for name, value in prior.items():
        assert sha(R / name) == value, 'Previously completed artifact changed'
    labels = dict(zip(MODELS, [primary, secondary, tertiary]))
    ids = [f['fact_id'] for f in facts]
    pairs = []
    for a, b in combinations(MODELS, 2):
        pairs.append({'model_a': a, 'model_b': b, 'all200': agreement(ids, labels[a], labels[b]),
                      'both_called': agreement(called, labels[a], labels[b]),
                      'by_original_primary_stratum': {s: agreement([fid for fid in called if primary[fid]['truth_status'] == s], labels[a], labels[b]) for s in CLASSES},
                      'common_binary_calibration': paired_calibration(facts, labels[a], labels[b], n_boot=2000)})
    report = {'at': utcnow(), 'models': MODELS, 'n_facts': 200, 'all_three_called': pattern_summary(called, labels, MODELS),
              'all200': pattern_summary(ids, labels, MODELS),
              'mechanical_no_evidence': pattern_summary(mechanical, labels, MODELS),
              'by_original_primary_stratum': {s: pattern_summary([fid for fid in called if primary[fid]['truth_status'] == s], labels, MODELS) for s in CLASSES},
              'pairwise': pairs, 'counts_all200': {m: dict(Counter(r['truth_status'] for r in labels[m].values())) for m in MODELS},
              'conditional_calibration': analyse_labels(facts, [r for m in MODELS for r in labels[m].values()], n_boot=2000, seed=20261002),
              'scope': 'Frozen primary-label-enriched sample:85supported+2contradicted+113/921unresolved; seed20261002. Descriptive diagnostics, not population agreement.',
              'limitations': ['All three are requested OpenAI model IDs; no cross-provider independence or architectural difference established.',
                              'CLI does not attest server model snapshots. Same evidence and prompt replayed.',
                              '11 mechanical unresolved items are excluded from actual three-model agreement.',
                              'Unresolved is not false; majority vote is not ground truth. No labels overwritten.',
                              'Each calibration estimate is conditional on binary coverage; pairwise deltas use the same facts and confidence scores.']}
    rows = []
    for f in facts:
        fid = f['fact_id']
        row = {'fact_id': fid, 'query_id': f['query_id'], 'claim': f['claim'], 'confidence': f.get('confidence'),
               'all_three_called': fid in called, 'statuses': {m: labels[m][fid]['truth_status'] for m in MODELS},
               'judgments': {m: {k: labels[m][fid].get(k) for k in ('truth_status', 'citation_status', 'reason', 'scope_notes', 'quotes', 'validation_status')} for m in MODELS}}
        row['distinct_statuses'] = len(set(row['statuses'].values()))
        rows.append(row)
    disagreements = [r for r in rows if r['distinct_statuses'] > 1]
    write_json(OUT / 'comparison.json', report)
    write_json(OUT / 'audit.json', {'at': utcnow(), 'status': 'passed', 'previous_artifacts_unchanged': len(prior),
               'secondary': {k: v for k, v in old_audit.items() if k != 'item_sha256'},
               'tertiary': new_audit, 'new_cli_invocations_this_extension': 189,
               'successful_additional_judge_invocations_cumulative': 378,
               'failed_historical_gpt6_invocations': 1})
    write_jsonl(OUT / 'tertiary_labels.jsonl', [{k: v for k, v in tertiary[fid].items() if k not in ('evidence_payload', 'raw_judgment')} for fid in ids])
    write_jsonl(OUT / 'fact_comparison.jsonl', rows)
    write_jsonl(OUT / 'disagreements.jsonl', disagreements)
    flat = [{k: r[k] for k in ('fact_id', 'query_id', 'claim', 'confidence', 'all_three_called', 'distinct_statuses')} | r['statuses'] for r in rows]
    with (OUT / 'fact_comparison.csv').open('w', newline='', encoding='utf8') as fp:
        writer = csv.DictWriter(fp, fieldnames=list(flat[0])); writer.writeheader(); writer.writerows(flat)
    all3 = report['all_three_called']
    text = f'''# 三模型多样性补评估

本轮新增第三Judge `gpt-5.6-terra`；此前为 `gpt-5.5` 与 `gpt-5.6-sol`。三个模型均请求medium reasoning，模型只收到相同原提示词及冻结证据。
第三模型200条全部处理：189次成功CLI模型调用，11条无可用证据、没有调用模型。先2条试运行，再执行其余样本。

189条三者实际调用模型的样本中，三者全部一致{all3['unanimous']}条（{all3['unanimous_fraction']:.2%}），有分歧{all3['any_disagreement']}条。
其中两者一致、一者不同{all3['two_agree']}条；三种判断各不相同{all3['all_different']}条。没有将多数票当作真值或改写原标签。

| 模型A | 模型B | 一致/实际双调用 | 一致率 |
|---|---|---:|---:|
'''
    for pair in pairs:
        a = pair['both_called']; text += f"| {pair['model_a']} | {pair['model_b']} | {a['agree']}/{a['n']} | {a['agreement']:.2%} |\n"
    text += '\n| 模型 | supported | contradicted | unresolved（含11条无证据） |\n|---|---:|---:|---:|\n'
    for m in MODELS:
        counts = report['counts_all200'][m]
        text += f"| {m} | {counts.get('supported', 0)} | {counts.get('contradicted', 0)} | {counts.get('unresolved', 0)} |\n"
    text += f'''
原样本按主Judge标签富集：85 supported、2 contradicted、113/921 unresolved，seed=20261002。上述比例描述固定样本，不能直接外推到1008条总体。
三者均为OpenAI通道上的不同请求模型ID；不能据此声称跨供应商、不同训练架构或独立专家验证。CLI没有返回服务端模型快照。

`comparison.json`包含三者判断组合、按原主Judge分层的一致性、每对模型的共同二元交集Brier/ECE差异、2000次query整簇bootstrap和各模型二元覆盖率。
条件calibration反映不同标签下的原存储置信度，不是新模型对事实输出的置信度；不同覆盖子集不能直接比较为性能高低。

逐条结果：`fact_comparison.csv`、`fact_comparison.jsonl`；全部{len(disagreements)}条分歧及三者原理由/引文：`disagreements.jsonl`。
完整性：`audit.json`。前两模型的{len(prior)}份样本、调用或结果文件hash全部不变，主评估1008条及9份受保护原文件也重新核验。第三模型原请求、输出、token记录在`../tertiary_judge_terra_v1/`。

仍需作者确认参考图、真实专家审核及另行完成重复/严格预算实验；新增模型多样性不替代这些工作。
'''
    (OUT / 'RESULTS_ZH.md').write_text(text)
    write_json(OUT / 'output_sha256.json', {p.name: sha(p) for p in OUT.iterdir() if p.is_file() and p.name != 'output_sha256.json'})
    print(json.dumps({'all_three_called': all3, 'pairs': [{k: p[k] for k in ('model_a', 'model_b', 'both_called')} for p in pairs],
                      'counts': report['counts_all200'], 'new_calls': 189, 'prior_hashes_verified': len(prior)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
