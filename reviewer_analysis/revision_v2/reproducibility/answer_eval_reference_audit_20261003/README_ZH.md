# Q4 答案评估、旧代码复现与 reference 版本追溯

2026-10-03。全部七方法、Q61–Q80、每方法一份历史生成结果。已完成：新答案协议两 Judge 共 280 条逐题分数，以及原算法在两种 reference 上各 140 条分数。没有重跑搜索 agent。

**关键发现：旧分数与新评估使用的 reference 不同。** 历史保存的 Q1–Q3 reference 与 `benchmark/scpqa.jsonl` 共 420/420 一致；全部 140 个历史 Q4 Recall 也与该文件的拆项分母兼容。这是强间接证据，历史 Q4 reference 哈希和匹配对仍未恢复。新协议使用的 `gt_q4.jsonl` 与它全部 20 道 Q4 都不同，正式版本及来源独立性仍待作者确认。不能因某版排名更高就选择它。

## 历史版本支持的旧算法复现

使用原评分源码和 `scpqa.jsonl`，Judge 替换为 GPT‑5.5。这里的“答案项 F1”仍是**旧逗号拆项与无一对一约束匹配**的结果，不是新协议的答案语义 F1。

| 方法 | 旧答案 P | 旧答案 R | 旧答案项 F1 | 旧复合分 |
|---|---:|---:|---:|---:|
| Helicase | 70.15% | 50.87% | **56.00%** | **54.84%** |
| Claude | 74.67% | 44.71% | 52.19% | 49.06% |
| ToT | 49.58% | 24.46% | 29.04% | 27.30% |
| DeepSeek | 32.32% | 21.58% | 22.09% | 20.76% |
| ReAct | 38.75% | 18.34% | 20.01% | 18.81% |
| GLM | 20.77% | 22.86% | 19.79% | 18.60% |
| Qwen3-235B | 21.96% | 17.11% | 13.83% | 13.00% |

Helicase 均值第一。与 Claude 的答案项 F1 差为 +3.82 pp，配对 95% CI 为 **[−12.47, +19.78] pp**；复合分差为 +5.78 pp，CI [−9.96, +21.41] pp，均跨零。不能宣称稳定显著领先。区间按 20 个问题 bootstrap 10,000 次，不代表独立 agent 运行方差，未做多重比较校正。

历史 Helicase 答案项 F1 **86.745%**、复合分 **85.285%** 尚未复现。旧 Judge 和采样设置不完全可恢复。保存的异常和缺失不能由本次复跑自动消除。

## 分开比较 reference 与算法

| 方法 | 历史答案项 F1，未核验 | 旧算法＋scpqa | 旧算法＋gt_q4 | 新协议两 Judge＋gt_q4，规则修正后 |
|---|---:|---:|---:|---:|
| Helicase | 86.75% | 56.00% | 21.82% | 29.27% |
| Claude | 67.26% | 52.19% | 25.40% | 39.16% |
| DeepSeek | 28.99% | 22.09% | 23.95% | 27.67% |
| GLM | 35.31% | 19.79% | 32.12% | 45.92% |
| Qwen3-235B | 26.20% | 13.83% | 20.75% | 15.96% |
| ReAct | 34.21% | 20.01% | 13.10% | 23.79% |
| ToT | 41.12% | 29.04% | 10.84% | 25.79% |

两个旧算法版本复用**完全相同的 140 份 GPT‑5.5 抽取回答**，只换 reference 重新匹配。Helicase F1 相差 34.18 pp，GLM 的方向则相反，说明 reference 版本足以影响排名；两轮 matcher 的随机差异仍未单独估计，不能把数值差全部解释为确定性 reference 因果效应。

新协议采用 GPT‑5.5 和 GPT‑5.6‑Sol，共享 517 个冻结的预测答案项。抽取器不看 reference，完整读取报告，保存精确引文，再按一对一匹配程序计算 P/R/F1，分别逐题宏平均。参考卡片与粒度审查由 AI 维护，不是独立人工 gold。正式版本确认后，仍需统一同一 reference，才能作新的主指标比较。

原始两 Judge 平均 Helicase F1 为 29.55%。执行 agent 的两处明确协议修正另存：移除 GLM/Q69 中把 Kenzo 理由挂在 Marc Jacobs ID 上的错误候选（已有正确 Kenzo 候选，分数不变）；移除 Helicase/Q80 将计划生产匹配为实际生产的配对（修正后均值 29.27%）。原始结果不覆盖。产品别名、粒度和保留态度仍存在争议。

原始匹配状态一致率为 94.78%，Cohen κ=0.8906，517 项中 27 项不一致。这不是人工真值准确率，也不是跨提供商独立验证。

## reference 差异为什么重要

- Q62：scpqa 列 Nesquik Go Vegetal、Nestlé 33 cl；gt_q4 列六个饮料系列。
- Q69：scpqa 给出否定／没有公开确认的表述；gt_q4 列八个品牌。
- Q73：scpqa 侧重设备类别、供应商和压缩机型号；gt_q4 列五种家电类别。
- scpqa/Q68 包含“provided report”措辞，若干 reference 与 Helicase 报告高度重合。是否独立于被评回答制定仍需核验；匹配分高本身不能证明来源独立或现实事实正确。

## 文件与复核

- [reference 版本哈希和逐份历史一致性检查](reference_provenance.json)
- [三路分数对照](comparison.json)
- 旧算法：[scpqa 逐题 CSV](legacy_scpqa_per_query.csv) · [分解与配对区间](legacy_scpqa_summary.json)；[gt_q4 逐题 CSV](legacy_gt_q4_per_query.csv) · [分解与配对区间](legacy_gt_q4_summary.json)
- 新协议：[原始 280 行](new_gt_q4_raw_per_query.csv) · [原始汇总与区间](new_gt_q4_raw_summary.json) · [修正后 280 行](new_gt_q4_reviewed_per_query.csv) · [修正后汇总与区间](new_gt_q4_reviewed_summary.json)
- [两处修正记录](protocol_corrections.json) · [Judge 一致性](judge_agreement.json) · [稳定独有命中数量](stable_unique_hits_summary.json)
- [运行条件及代码哈希](run_conditions.json) · [调用数量与 CLI token 记录](call_accounting.json) · [完整性检查](integrity_checks.json)
- [新协议源码与限制说明](../../ANSWER_BLIND_V4_ZH.md) · [旧源码快照](../historical_q4_metric_20261003/eval_scpqa.py)

公开数值可以离线核算：

```bash
python reviewer_analysis/revision_v2/reproducibility/answer_eval_reference_audit_20261003/verify_public.py
```

公开包包含数值、代码、哈希和协议，不包含私人原报告、reference 全文、模型原回复或完整配对。因此公开 CSV 能检查算术，**不能单独证明语义配对正确**。这些原始材料及逐题命中／遗漏／额外项表保留在本地 private 目录。没有修改 `paper/main.tex` 或在线 rebuttal；统一跨方法引用支持、独立专家标签和预算匹配重跑仍未完成。
