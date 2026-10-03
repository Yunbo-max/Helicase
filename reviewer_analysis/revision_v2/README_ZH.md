# Helicase / IJPR 268226721：旧复合评估 + 新证据评估

版本：`answer-evaluation-reference-audit-v1`，2026-10-03。历史协议继续保留，最新执行状态以下方结果包为准。

**保留原 SCQA、文本 reference、原报告、原生 KG 和历史评分；保留旧复合代理评分的研究思路。新增主张与引用证据评估，不再默认要求建立完整 gold graph。** 自定义代理指标可以保留，但须公布真实公式和用途；它不是逐关系准确率。异常计数仍需核对，不能由新增指标自动消除。

**本次已完成旧回答的补评分并公开数值与适配器代码，没有重跑搜索 agent，也没有修改历史原分数或论文正文。**

最新入口：[**Q4 新旧评估结果与 reference 版本追溯**](reproducibility/answer_eval_reference_audit_20261003/README_ZH.md) · [盲抽取及旧代码复现协议](ANSWER_BLIND_V4_ZH.md)。

- 原算法＋GPT‑5.5＋历史记录支持的 `scpqa.jsonl`：140/140 完成，Helicase 旧答案项 F1 **56.00%**、复合分 **54.84%**，均值第一；对 Claude 的配对区间跨零，历史 86.745% 尚未复现。
- 原算法＋GPT‑5.5＋`gt_q4.jsonl`：140/140 完成，复用相同抽取回答，Helicase 旧答案项 F1 **21.82%**。
- 新答案协议＋GPT‑5.5／GPT‑5.6‑Sol＋`gt_q4.jsonl`：280/280 完成；原始和规则修正结果分别保留，Helicase 双 Judge 平均 F1 为 **29.55%／29.27%**。

**两份 reference 的全部 20 道 Q4 都不同。** 历史 Q1–Q3 留存 reference 与 scpqa.jsonl 420/420 一致，Q4 分母全部兼容；历史 Q4 reference 哈希仍缺失。正式 reference 版本和来源独立性待作者确认，不能直接把上述不同口径分数解释为方法变好或变差。新协议在确认的历史版本上尚未执行。

## 先读哪份

- [旧评估：要复核/补跑什么、精确公式、工作量与验收](LEGACY_EVAL_RUNBOOK_ZH.md)
- [新评估：无需完整参考图的主张/引用方法与公平规则](CLAIM_EVIDENCE_PROTOCOL_ZH.md)
- [英文 rebuttal 说辞与 Changes in the manuscript](REBUTTAL_EVALUATION_TEXT.md)
- [总体实验边界及预算/重复运行](EXPERIMENT_PROTOCOL.md)
- [执行结果状态模板](REMAINING_STATUS_TEMPLATE.md)
- [旧指标源码说明](OLD_Q4_METRIC_ZH.md) · [既有运行记录](VALIDATION.md) · [完整历史命令手册](README_FULL_ZH.md)

## 1. 已做完的，不要原样重跑

下面是既有仓库记录中的结果，不是本次重新检查了所有私有标签。

| 工作 | 已有记录 | 现在如何使用 |
|---|---|---|
| 原归档导入 | 7 方法 × 80 题 | 复用原 reports / native graphs / reference texts |
| 全文报告图抽取 | 140/140 | 留作探索性图视图；已知抽取问题不被结构通过掩盖 |
| 暂定全文图匹配 | 140/140；Helicase 0.2097，六个配对差值区间均含 0 | 保留结果及局限；不替代旧尺度，也不因不利而删除 |
| 引用页面 | 484 个有处理记录，426 可用 | 复用原快照；不全量重新抓取 |
| 原生边主判断 | 1,008：85 supported、2 contradicted、921 unresolved | 复用标签；unresolved 不是错误 |
| 条件校准 | 87/1,008 可二元判断（8.63%）；Brier 0.052989，ECE 0.157471 | 说明子集和来源标签；不称全图校准 |
| 三模型检查 | 固定 200 条，其中 189 条实际三模型调用；150 一致、39 分歧 | 已完成的原生边诊断，不重加第四个 Judge；不是新答案评分器已验证 |
| 人工审核材料 | 400 条空白独立表 | 复用；没有真实填写就没有 human IAA |
| 旧评分定位 | 找到代码；140 条关系代理公式与归档吻合 | 原定义已查清；历史匹配对与真实模型快照并未因此恢复 |

来源：[VALIDATION](VALIDATION.md)、[三模型记录](reproducibility/model_diversity_20261003/README_ZH.md)、[暂定图匹配](reproducibility/provisional_graph_matching_20261003/README_ZH.md)、[旧代码出处](reproducibility/historical_q4_metric_20261003/provenance.json)。

## 2. 剩余任务，按这个顺序执行

| ID | 任务 | 调用需求 | 当前入口/状态 |
|---|---|---|---|
| O0 | 冻结输入与异常核对 | 零 API | 已执行；发现两版 reference 全部 Q4 不同，正式版本待确认 |
| O1 | 拆出答案 P/R/F1、结构项和复合分 | 零 API | 已公开两版旧算法逐题分解；历史匹配对仍缺失 |
| O2 | 七方法 × 20 题统一答案重评 | Judge，不搜索 | gt_q4 的双 Judge 和两版旧算法均已完成；确认正式 reference 后再统一主指标 |
| O3 | 配对 CI、结构项及边界测试 | 离线 | 已计算逐题宏平均和配对区间；共享抽取与 AI 参考维护的误差不由区间覆盖 |
| N0 | 冻结并汇总现有引用判断、覆盖率、条件校准和三模型诊断 | 零 API | 已有结果复用；标准标签格式可用 `analyse` |
| N1 | 只为缺少的跨方法“回答主张”样本补充引用判断 | 按缺项调用 | `judge` 可用；新样本/视图适配尚需准备，不能混用 native edge 与 narrative claim |
| H1 | 真实独立专家核验与案例审核 | 人工 | 复用表；`agreement` 计算实际独立评分一致性 |
| B1 | 查已有 ablation/run 配置，决定尚缺的预算/重复证据 | 先零 API | 不默认启动 240 次；不能以重新评分冒充 agent 重复 |

**本批不以“Helicase 必须第一”为完成条件。** 合理的保护是同一题目、同一抽取/匹配规则、同一证据预算，不让输出格式或篇幅造成无关惩罚；错误主张也不能因为方法名而被忽略。

## 3. 执行入口与费用闸门

```bash
git status --short
git pull --ff-only origin main
python -m reviewer_analysis.revision_v2 --help
```

不要使用 `reset --hard` / `clean` 清理本地研究结果。先读 O0–O3；输入路径从实际 `private/` 定位，不新造空目录代表已完成输出。

现有 `pages`、`judge`、`analyse`、`paired`、`agreement` 可复用。**本次没有新增 `answer-eval`、`legacy-rerun`、`no-uq` 或四系统预算匹配命令。** 不要猜命令名。已新增 `answer_blind.py`、`legacy_replay.py` 等 Python 适配器；本批私人编排记录保留本地，不能把模块当作统一新 CLI。公开结果包的 `verify_public.py` 可直接离线核算，无需 key。后续不重复已完成输入。

本批按作者要求在隔离适配器中复现了原算法，包括已知计数问题，并逐项保存异常；它是诊断，不是把这些问题认证为正确。旧均值不能反推出两次真实运行，更不能导入个人占位工作表作为实验数据。

## 4. 停止条件与交付

O0/O1 后若缺原报告、reference、原生图或运行身份，记录 `blocked`，不要补造。O2 若需要新标签，先冻结所有方法的输入和规则；任何修改另建版本，保存前后差异与原因。相同成功任务不重复调用。

在本地创建 `private/complementary_eval_v1/REMAINING_STATUS.md`，按[模板](REMAINING_STATUS_TEMPLATE.md)记录每项为 `completed / reused / planned / blocked / not_run`。附真实路径、输入哈希、计数、实际模型配置、错误及适用范围；不得把“已生成脚本/表格”标成“真实实验完成”。

本轮收尾以“旧指标定义与异常说明 + 经核验的答案/复合分拆分 + 引用证据与覆盖 + 独立人审状态”为准。完整图 gold 不再是本批闸门；标注记录、测试独立性、预算与执行稳定性仍是独立审稿要求，不宣称自动关闭。
