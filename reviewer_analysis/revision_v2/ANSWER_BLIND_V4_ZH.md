> **当前已完成：作者确认的 scpqa.jsonl × 原 V4 冻结预测项 × GPT‑5.5/GPT‑5.6‑Sol，共 280 条评分。主要结果见[新版 scpqa 结果](reproducibility/answer_eval_scpqa_20261003/README_ZH.md)。gt_q4 结果仅作版本对照；旧分数复现不是当前任务。冻结预测中的 epistemic exclusions 与 scpqa 的适配限制保留披露。**

# Q4 新答案语义评估协议

本轮按作者确认的协议执行：答案语义 Precision、Recall、F1 为主，三项分别逐题宏平均；旧复合分及结构项仅保留归档；引用支持单独报告。全部七个方法、Q61–Q80 使用原存档报告，不重跑搜索 agent。

## 新协议

`answer_blind.py` 把预测答案盲抽取与参考匹配分开。抽取请求只有匿名 source_id、问题、完整报告；不含 reference、方法名和历史分数。不做 8,000 字符截断，不限制答案句数。每个单位保存完整关系、状态、精确连续引文和出处。

140 份报告分 44 个请求抽取，随后按问题进行 20 个参考盲化的粒度整理请求。每个整理单位必须指回本来源的输入 ID；所有输入必须有去向，不得借用其他来源的答案。短报告的抽取批次只包含同一方法的不同问题；粒度整理阶段七来源匿名同题输入，模型被要求逐来源独立处理。因此这不是七来源完全独立的抽取复现实验。

在匹配前审查全部否定单位，将“没有公开确认”、正向答案后的“没有其他已确认项”、被明确排除的候选和工艺说明与真实否定答案区分。保存原输出、审查理由和前后单位，不能覆盖原报告。Q64、Q76 的粒度执行错误有单独修复记录。参考卡片来自原文字答案，由执行 agent 维护，尚非独立人工 gold。

冻结后，GPT‑5.5 与 GPT‑5.6‑Sol 读取相同单位、reference 和计数说明。两者只能给配对与理由；程序验证 ID、进行最大一对一匹配并计算 `P=m/Np`、`R=m/Nr`、`F1=2m/(Np+Nr)`。无预测答案时 P/R/F1 均记 0；失败调用不是零分，必须单独处理。空 reference 不允许进入当前数据集。

汇总先按题计算，再分别平均。按 20 个问题配对 bootstrap 10,000 次；两个 Judge 的平均也先在同一道题内平均，再重采样问题。完整展示全部方法、全部配对差值、命中／遗漏／额外项及 Judge 分歧。额外项只表示 reference 未匹配，不自动等于事实错误。

V3/V3.1 抽取看过 reference，与此次协议不兼容，仅保留为诊断。V4 仍属事后修订评估，抽取和参考维护共享 AI 误差；两个同提供商 Judge 的一致性不能替代人工效度核验。

## 归档：原代码复现（不再是当前待办）

`legacy_replay.py` 执行归档 `reproducibility/historical_q4_metric_20261003/eval_scpqa.py`，不修改其评分代码。原代码和当前 `benchmark/eval_scpqa.py` 在准备输入时字节相同。

复现保留报告前 8,000 字符、1–3 句抽取、逗号／分号拆项、匹配前 30 项但按全量项作分母、多对多计数、未校验成员身份以及密度代理复合公式。每次保存原 prompt、原回答、匹配对、完整精度分解和原代码三位小数输出；越界值与不合法配对只做标记，不裁剪。

唯一模型路径替换是使用 GPT‑5.5 的 Codex CLI；不再依赖旧 Qwen/SiliconFlow API。旧代码请求 temperature=0，Codex CLI 无法独立设置或核验这一参数。故这是**原算法在替换模型上的复现**，不是历史模型环境的逐位复现。旧抽取器吞异常后的静默回退不能被记为成功，本次外围执行器会记录失败并停止该项。

## 本地结果与覆盖

当前公开结果见 [scpqa 新协议结果包](reproducibility/answer_eval_scpqa_20261003/README_ZH.md)，对应私人输出为 `private/complementary_eval_v1/answer_blind_scpqa_v1/`。以下是归档目录： `private/complementary_eval_v1/answer_blind_v4/`、`private/complementary_eval_v1/legacy_replay_gpt55_v1/` 和 `private/complementary_eval_v1/legacy_replay_scpqa_gpt55_v1/`。以各目录 `progress.json`、`status.json` 和最终结果文档确认实际完成度，不把执行协议当作结果。

原历史值、旧流程新复现值、新答案语义值分开保存。已有原生边引用诊断可复用；统一跨方法引用支持率、独立人工评分与严格预算匹配独立 agent 运行未因此完成。
