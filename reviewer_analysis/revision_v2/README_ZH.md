# Helicase / IJPR 268226721：旧复合评估 + 新证据评估

版本：`complementary-evaluation-v1`，2026-10-03。以已核对的 `ccad149` 为资料基线。

**保留原 SCQA、文本 reference、原报告、原生 KG 和历史评分；保留旧复合代理评分的研究思路。新增主张与引用证据评估，不再默认要求建立完整 gold graph。** 自定义代理指标可以保留，但须公布真实公式和用途；它不是逐关系准确率。异常计数仍需核对，不能由新增指标自动消除。

本次是文档与执行要求更新，**未运行新实验，未改核心代码、评分实现、论文正文或原始结果**。下表区分现成工具、待适配工作和人工任务，不能把方法说明读成已接通的 CLI。

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
| O0 | 冻结原文件，检查 Q68/Q73 和所有方法同类异常 | 零 API | 本地检查；不得覆盖历史记录 |
| O1 | 拆出答案 P/R/F1、密度项和旧复合分；统一有效性审计 | 零 API | 需本地保真字段适配；不是新 CLI |
| O2 | 无法核验旧匹配时，重评固定 Q4 的答案项，并计算同一复合公式的新版本 | 可能调用 Judge，不搜索 | 新答案项适配器需按 runbook 实现/测试；现有 `extract/match` 是全文图评估，不能冒充此任务 |
| O3 | 答案分数与复合分数的配对 CI、结构权重敏感性及评分器边界测试 | 主要离线 | `paired --metric` 可处理合规逐题分数；测试/拆分需本地适配 |
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

现有 `pages`、`judge`、`analyse`、`paired`、`agreement` 可复用。**本次没有新增 `answer-eval`、`legacy-rerun`、`no-uq` 或四系统预算匹配命令。** 不要猜命令名。新的答案项适配器是明确的待实现要求；先做无网络单元测试，再最多两项 pilot，确认数据流正确后才继续固定清单。pilot 不是按得分挑提示词。

原 `benchmark/eval_scpqa.py` 是历史快照，不要直接启动全量重评以复制已知无约束匹配。旧均值不能反推出两次真实运行，更不能导入个人占位工作表作为实验数据。

## 4. 停止条件与交付

O0/O1 后若缺原报告、reference、原生图或运行身份，记录 `blocked`，不要补造。O2 若需要新标签，先冻结所有方法的输入和规则；任何修改另建版本，保存前后差异与原因。相同成功任务不重复调用。

在本地创建 `private/complementary_eval_v1/REMAINING_STATUS.md`，按[模板](REMAINING_STATUS_TEMPLATE.md)记录每项为 `completed / reused / planned / blocked / not_run`。附真实路径、输入哈希、计数、实际模型配置、错误及适用范围；不得把“已生成脚本/表格”标成“真实实验完成”。

本轮收尾以“旧指标定义与异常说明 + 经核验的答案/复合分拆分 + 引用证据与覆盖 + 独立人审状态”为准。完整图 gold 不再是本批闸门；标注记录、测试独立性、预算与执行稳定性仍是独立审稿要求，不宣称自动关闭。
