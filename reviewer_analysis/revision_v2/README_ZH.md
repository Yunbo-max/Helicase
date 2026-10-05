# Helicase / IJPR：Q4 新版答案语义评估

## 补充完成：同一批新报告的旧算法重评

**2026-10-05，按作者要求，80 份新报告的原版旧 Q4 算法重评已完成。** 使用 `scpqa.jsonl` 和 GPT-5.5，旧复合分 Helicase **34.83%**、Uniform-planning KG **29.35%**；差 **+5.48 个百分点**，20 题配对 95% CI **[−5.17, +15.64]**。Helicase 均值更高，区间包含 0。旧答案片段 F1 分别为 **34.94% / 29.44%**，结构项单列。

这是事后补充的旧算法加替代评委重评，保留旧截断和匹配计数行为；下方新协议及旧七方法结果不改写。[旧算法完整结果、异常、用量与离线复算](reproducibility/planning_legacy_gpt55_20261005/README_ZH.md)。

## 最新：两个方法的真实重复运行

**2026-10-05，两组 × 20 道 Q4 × 两次独立运行，共 80 次执行及统一评分完成。** Helicase（调用与工具上限控制版）答案 P/R/F1 为 **23.56% / 37.19% / 26.75%**；Uniform-planning KG 为 **17.37% / 33.44% / 21.21%**。F1 差 +5.54 个百分点，20 题配对 95% CI **[−3.08, +13.71]**，包含 0。

72 次完整和8 次部分完成全部纳入，同为 GPT-5.5、相同 CLI/搜索/读页上限，token 仅记录 CLI 报告用量，不严格匹配。评分的一项引用大小写恢复、失败调用及协议限制均明确保留。**这批新报告与下方旧七方法报告的重评分不是同一批实验。**

- [80 次结果、重复均值/SD、资源与异常说明](reproducibility/planning_gpt55_20261005/README_ZH.md)
- [80 条逐次数据](reproducibility/planning_gpt55_20261005/per_execution.csv) · [20 题的两次均值](reproducibility/planning_gpt55_20261005/per_query.csv)
- [本地运行与复现说明](PLANNING_RUNBOOK_ZH.md)

## 既有七方法报告：统一答案重评分

**新答案协议 + 作者确认的 `scpqa.jsonl` 已完成。** GPT‑5.5 和 GPT‑5.6‑Sol 对同一批 517 个冻结预测项完成匹配，共七方法 × 20 题 × 两评委的 280 条评分。没有重新抽取或搜索，也不再追查历史高分。

**Helicase 双评委平均 Precision 49.30%、Recall 65.83%、F1 54.85%，F1 均值第一。** Claude 为 52.66%，ToT 27.33%，ReAct 21.52%，GLM 19.30%，DeepSeek 17.23%，Qwen3‑235B 8.60%。Helicase 对 Claude 的 F1 差为 +2.19 个百分点，配对 95% CI [−9.82, +15.24]，不能称为统计上明确领先 Claude。

- [完整结果表、分模型结果与配对区间](reproducibility/answer_eval_scpqa_20261003/README_ZH.md)
- [280 条逐题评分](reproducibility/answer_eval_scpqa_20261003/per_query_scores.csv)
- [新答案协议](ANSWER_BLIND_V4_ZH.md)
- [旧结果及 gt_q4 版本归档](reproducibility/answer_eval_reference_audit_20261003/README_ZH.md)

## 覆盖与限制

本轮严格复用 V4 冻结预测项。此前抽取排除了部分“没有公开确认”的回答，Helicase 在 Q63/Q65/Q68/Q69/Q72/Q75 为零个保留预测项，按相同规则计零；Q68 原始报告本身没有实际回答。该限制和全部方法的零预测覆盖已披露，本次没有为提高排名补写答案。

参考卡片由 AI 按原文维护；作者确认 reference 文件，不代表独立人工审核或来源独立性已验证。双评委一致率 98.65%，仍有 7 项匹配状态分歧；原始判断保留。这批七方法报告再评分本身不提供统一引用支持率、独立专家核验或真实重复运行证据；已完成的两组调用/工具上限控制实验见本页上方，仍不宣称严格 token 匹配。

## 离线复核

```bash
python reviewer_analysis/revision_v2/reproducibility/answer_eval_scpqa_20261003/verify_public.py
```

无需 key，检查 280 条评分、公式、宏平均、输入数量和公开文件哈希。完整匹配对、命中／遗漏／额外项、原始回复与一次格式失败修复保存在 `private/complementary_eval_v1/answer_blind_scpqa_v1/`。共 40 个成功匹配任务、41 次 CLI 调用；未修改原始报告、reference、历史结果或论文正文。
