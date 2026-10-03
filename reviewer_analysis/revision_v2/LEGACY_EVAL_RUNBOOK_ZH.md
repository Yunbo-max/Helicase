# 旧评估：保留复合代理指标，并明确需要补做的实验

版本 `complementary-evaluation-v1`。这是拟执行协议，不是新结果。来源：[历史代码](reproducibility/historical_q4_metric_20261003/eval_scpqa.py)、[公式审计](OLD_Q4_METRIC_ZH.md)。不要求完整 gold graph，也不修改 Helicase 核心算法。

## 1. 保留对象和命名

保留原问题、文本 reference、报告、原生图、配置和旧分数。表述为 **legacy composite proxy score**。这是一种自定义复合评分，不能称其直接测量真实关系 precision/recall。旧名称可在历史记录中标明，但不是新的语义保证。

分别保存 `historical_as_reported`（不可改写）、`recomputed_legacy_composite_v1`（新匹配下的同公式）和 `answer_units_v1`（不含结构调整）。三者不能混作一个指标，也不能把重新评分写成 agent 新执行。

## 2. 精确公式：按代码而不是事后叙事

设答案片段 precision、recall 为 P、R，A=H(P,R)，其中 H(x,y)=2xy/(x+y)，分母为零时取 0。V 和 E 为按旧 helper 去重后的原生节点名和有向三元组数量。

- 有原生节点且有关系：d=min(1,E/max(V,1))，a=0.8+0.2d，P_proxy=aA，R_proxy=aR。
- 否则：P_proxy=0.85P，R_proxy=0.85R。
- R_proxy_F=H(P_proxy,R_proxy)，L=0.6A+0.4R_proxy_F。
- 旧单题 discrepancy=abs((1-final_memory)-L)，只在 final_memory 存在时计算。它不是 per-fact ECE/Brier。

E/V 是边节点比而非常规定义的图密度；保留历史命名时说明这一点。结构项不比较预测边与参考边。即使 P=R=1，无原生图得 L=0.94，有图且 d=1 得 L=1；这是代入公式的例子，不是新实验。

旧代码只匹配前 30 片段却使用全列表分母；返回字符串没有输入成员及一对一验证。源模型由 EVAL_MODEL/READER_MODEL 等运行设置决定；默认模型不证明实际历史模型。140 条公式吻合不恢复历史 Judge 原始判断。

## 3. O0：冻结与异常清单（零 API，先做）

记录每个 method/run/query 的原问题、报告、reference、原生图、评分文件、模型配置与哈希。旧运行版本无法确定就明确 unknown。逐题确认 Q61–Q80 各方法均齐全，不能仅检验表格平均数。

核查 Q73 超范围分数、Q68 无实质答案高分，以及七个方法中的全部同类情形。先判断文件错配、缺失正文还是评估失败，不直接假定某一种原因。不得 clip 为 1、删除低分题或补写缺失答案。若确认记录只有题目且没有作答，新版本标记 abstention/no_answer；若只是文件缺失则 blocked，不把两者混为零分。

交付：`input_manifest.json`、`integrity_issues.csv`、`version_reconciliation.md`。存在不可定位的输入缺失时停止对应比较；不得只汇总成功题并称全量表现。

## 4. O1：旧分数拆分与代理行为检查（零 API）

按旧代码的 native 去重规则重建 V/E，逐行输出 P、R、A、d、分支、R_proxy_F、L、L-A、final_memory discrepancy。使用已有未舍入值；只有三位舍入值时记录容差，不宣称逐位复现。单列原归档分数及差异，禁止原地覆盖。

原数字有效的记录可用于描述性拆分；混有未解决异常时不输出“全部20题已验证”的排名/CI。将原始全表、异常清单及有限诊断的分母一起保存。

离线测试：固定答案与 V/E，仅重接/改写图关系，L 应不变；去掉原生图时应进入 0.85 分支。该测试说明代理的测量边界，不是证明结构正确，也不是要求改变公式使某方法获胜。

交付：`legacy_components.csv`、`formula_checks.json`。这是本地适配要求；本提交没有新增对应 CLI。

## 5. O2：仅在匹配不可核验时补跑答案评估（模型，不搜索）

先复用真实保存的答案提取与匹配记录。若如当前审计所述未保存可核对匹配，则对固定七方法×20 Q4统一重评，不仅重评 Helicase 或异常题。

### 5.1 冻结答案单位，不偷偷建立完整图

从原问题和原文本 reference 定义 task-relevant answer units。产品枚举以符合条件的产品为单位；供应关系题保留供应双方及关系；否定、计划/取消、版本、时间、地域、产品/工厂限制必须保留。不枚举全文所有背景节点或推断未写出的路径。

reference 单位只从原 reference 抽取，由作者核对其忠实性；不看各方法分数或用预测补造 reference。预测单位只从各自原报告提取，提取器看不到 reference、方法名和评分。每个单位包含稳定 ID、原文连续引句及偏移、claim 内容和适用范围。问题是上下文，不是答案证据。

旧 8000 字符/1–3 句压缩只在精确历史重放中保留并显式标注覆盖。本次修正版要求全报告可定位覆盖，不能给短答案完整读取而把长报告尾部丢弃。需要分块时所有方法用同一规则，保留分块/遗漏日志；费用上限不足则报告 incomplete，不能假装完整。评估消耗单独报告，不能算成原 agent 搜索预算。

新答案单位视图不是旧逗号片段的逐字复现；仍可用第2节相同公式计算 L_recomputed，并如实标为新评估版本。

### 5.2 匹配与评分

Judge 输出候选匹配 ID 对与对应原文理由，不输出分数。验证 ID 属于输入、没有重复或未知项；对可接受候选图采用统一的一对一选择规则，保存候选与最终配对。别名/反向同义关系先按冻结规范处理，不能合并公司与工厂、能力与实际供货。

令 m 为最终匹配数、Np/Nr 为去重后全体答案单位数量：P=m/Np，R=m/Nr，A=2m/(Np+Nr)。无预测且 reference 非空时 A=0；reference 意外为空为人工待核验，不自动给满分。显式否定答案是有效答案单位，不能当空集。

主分母只包括回答问题的单位，错误或不受支持的直接答案不能被抽取器删掉。背景内容不混进答案 F1，但在新证据评估中单列抽样审核。unmatched 是 reference-relative 未覆盖，不自动等于世界中错误。新增答案若要纳入 reference，须独立确认、版本化并对所有方法统一重评。

计算 A 与同一旧结构公式 L_recomputed，二者并排。结构分支差异是指标性质，必须公开；不以此宣称原比较已经预算匹配或结构真实性更高。

### 5.3 工作量与闸门

在没有可复用标签、每份报告一批就能容纳的情况下：20 份共享 reference 单位 + 140 份预测单位 + 140 份匹配，约 **300 个逻辑任务**。长报告分块、失败修复会增加调用；缓存会减少调用，不能将300保证为HTTP请求数或费用。

先做无网络测试，再固定最多两项 pilot。因有效性修改提示词时开新版本并统一影响范围，不按分数反复调试。全部配置冻结后才继续任务清单。只修无效记录，成功低分不重试；保存所有失败与修复。实际 provider/model/version、提示词、输入哈希、用量与调用时间均落盘。

当前仓库 `extract/match` 是全文图视图，**不能直接运行并声称完成 O2**。答案单位提取/匹配适配器尚需本地实现；本次只给出严格接口要求，不提供假 CLI。

## 6. O3：旧路线需要补的统计，不再扩张实验范围

必做：逐方法20题 A 与 L_recomputed 的宏平均；答案 P/R 分解；同题配对差值和 query-bootstrap CI。保留所有预先指定比较，明确比较的多重性；不选出显著对子才报告。单次运行只能报告 query 间不确定性，不能输出真实跨-run SD。

必做：单列结构贡献 L_recomputed-A 的分布及有图/无图比例，揭示结构项是否改变排名。不要称此差值为图准确性提升。

可做且零 API：在固定同一答案标签/原图上报告完整权重网格 w∈{0,0.25,0.4,0.5}，L_w=(1-w)A+wR_proxy_F。w=0.4保留历史定义；其它值只作事后敏感性分析，不选择最有利的w替换主指标。

必做软件检查：重复答案不加分、别名只计一次、未知匹配ID被拒、否定/计划不与实际供货混同、长文尾部答案不无声丢失、题目本身不作为答案、所有正常计数在[0,1]。这些是合成单元测试，不进入SCQA结果。

如果补做答案评分器第二Judge，只在预先冻结且覆盖方法/题型的样本上、使用相同单位/证据检查。已有三模型实验评的是原生边，不自动验证O2；无此实验就不声称答案指标跨Judge稳定。不默认再给所有140份跑三遍。

Q1–Q3的原结果保留；检查共享helper受影响范围，记录依据后只补需要重评的部分，不凭Q4异常否定整个数据集。

## 7. 下游工具接口与交付

合规逐题 JSONL 至少包含 `method, run_id, query_id, answer_f1, legacy_composite, evaluator_version, input_hash`，另存全部单位和配对。不得把这张表伪装成新agent执行。预期题号文件每行必须有 `query_id`。

现有离线工具可在合规适配完成后使用（路径为占位，不会创建输入）：

```bash
V=reviewer_analysis.revision_v2
export SCORES='/实际新版本/verified_answer_scores.jsonl'
export EXPECTED='/实际冻结题号/expected_q4.jsonl'
export OUT='/新的本地输出目录'

python -m "$V" paired --scores "$SCORES" --method-a Helicase --method-b ReAct \
  --metric answer_f1 --expected-queries "$EXPECTED" --out "$OUT/answer_Helicase_ReAct.json"
python -m "$V" paired --scores "$SCORES" --method-a Helicase --method-b ReAct \
  --metric legacy_composite --expected-queries "$EXPECTED" --out "$OUT/composite_Helicase_ReAct.json"
```

同规则处理全部计划比较；不得覆盖已有路径。交付 `answer_units/`、`match_pairs/`、`verified_answer_scores.jsonl`、`legacy_components.csv`、`paired_summary.json`、`weight_sensitivity.csv`、`REMAINING_STATUS.md`。所有表可显示两位小数，计算使用完整精度；无法定义的SD保持缺失，不以人为数值填补。
