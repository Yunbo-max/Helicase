# 新评估：主张与引用证据，作为旧复合指标的互补

协议 `complementary-evaluation-v1`。已有结果见[运行记录](VALIDATION.md)；本文件中的新增取样/适配是方法要求，不是已完成结果。无需构建穷尽的正确供应链 graph。

## 1. 为什么增加这一层

旧复合指标描述答案匹配和原生图结构项的组合。新层单独检验“一个具体主张是否获得所引用材料的支持”。不把两者强行换算成同一分数，不以图密度替代真实支持，不因额外背景多就降低答案F1。声明为 complementary evaluation，而非保证其能恢复某个排名。

来源参考是原文本答案，不是完整真实世界图。主张审核不需要知道所有可能的关系：只需检查本次预测的具体内容与原始证据。参考外主张可以被来源支持；未入reference不自动等于错误，也不自动获得正确标签。

## 2. 保持两个输出视图独立

**视图 A：原生 Helicase 边的证据诊断。** 已有1,008条主判断和三模型子集直接复用。它评价保存的原生边，不代表七个方法共同的答案比较。

**视图 B：各方法回答中的主张。** 用与旧路线 O2 一致的、问题相关的原文主张单位；预测提取不看reference、方法名、confidence或期望排名。七方法用同一规则，不把Helicase原生边与baseline全文句子混合成可比准确率。实体仅名字相同不等于关系正确，主张必须保留限定信息。

视图A结果不能自动复制为视图B标签。确实相同的主张、引文、证据字节、作用域、提示词和assessor版本才允许有映射记录的缓存复用；近似相同不能直接复用。

## 3. 主张单元与证据包

每条至少记录：`claim_id, method, run_id, query_id, view, claim_text, report_quote, report_offsets, subject, predicate, object, assertion_modality, scope, citation_urls, source_snapshot_hashes`。来源缺失也须显式记录。

- scope：产品/型号、公司或工厂层级、地点、有效期/报告日期；原文未知则unknown，不补造。
- assertion_modality：明确事实断言、被报道关系、推断、候选、能力、计划、取消、否定等按内容标注。`reported`与`physical_flow_claim`不是简单互斥真值；先核对实际语义，不能仅因字符串不同就判不等价。
- citation：给出具体页面及支持片段，而不是仅有域名；抽取quote验证的是忠实转录，不等于网页或主张为真。
- company supplies ingredient与ingredient enters particular product的关系不同；planned delivery不能升级为已发生物理流。

Judge只看到待评主张及固定证据包，不看系统身份、原score、其他Judge判断或方法优劣要求。不能调用工具自行搜索，也不能用预训练记忆补证据。

先冻结原有快照与实际展示片段。公平比较使用同一上限/选择规则，并记录实际每条展示来源数、字符数和遗漏；若片段截断可能遗漏关键支持，先离线定位。扩大证据上下文须新版本且对同类情形全部方法一致，不只救某方法的低分。

## 4. 可控的新增取样，不重做已完成批次

N0先复用现有 native-edge 评估、unresolved诊断、三模型结果；不新增第四Judge。

只有需要“跨方法引用支持更好”的结论时才执行N1。建议的有限设计是20条Q4×7方法、每个method/query最多3个直接答案主张，**上限420条**；这是新提案，不是已抽好的样本或既有400人审样本。

从冻结全部候选单位中均匀随机抽取，选中少于3条时全取；不能由作者挑最容易核验的事实。记录抽样种子、每层候选数、入样数与入样概率，固定后再看标签。方法名不提供给提取器/Judge。选择短语/句子不能过滤掉直接答案中的错误内容。

没有答案时保留method/query记录及abstention，不从总体题目分母消失。没有引用的回答记作citation_not_provided，不能默认为事实错误，不能给无web基线补上Helicase发现的来源后称为原输出的引用能力。

直接答案主张是N1主视图。额外背景另列为探索性审核，不能既从答案分母排除又宣布全文所有内容可靠。若比较总体micro支持率，须使用合理的抽样权重；相同每query限额不等于全体claims的等概率抽样。优先报告同一题目的宏平均、样本量与覆盖。无需为“多元化”再全量评估1,008条相同输入。

## 5. 标签与统计分母

事实判断保留三态：supported / contradicted / unresolved。它们是**相对于给定证据包的assessment**，不是世界真值。

另外记录 citation_status（例如supported、not_supported、not_provided、unavailable、unclear），以及 extraction_invalid / model_error / not_started 等流程状态。流程错误不是世界错误；自动无证据unresolved与模型实际调用结果分开计数。

设计划样本为T，其中得到有效证据判断的S/C/U分别为三态计数，流程错误为E，则T=S+C+U+E。报告：

- `supported / T`、`contradicted / T`、`unresolved / T`、`error / T`，不只给S/(S+C)。supported/T是确认支持比例，不是全体真实accuracy。
- citation_present、page_available、actual_model_called、引文可解析比例，分母分别说明。无引用和无可用页面不能无声排除。
- 可二元判断覆盖(S+C)/T及条件支持率S/(S+C)，分母为0时NA。
- claim–citation pair的支持率与claim层“至少一个引用支持”分开，防止靠堆引用掩盖不支持的页面。

语义同义和方向规范化对所有方法一致；字符串不同不自动失败，断言强度不同也不自动视为相同。绝不以多数票取代人工真值或把unresolved重标为false。

## 6. 校准与多Judge：复用已经做的，明确覆盖

对保存有confidence且被二元评判的相同原生事实，Brier=mean((c-y)^2)；固定分箱ECE按箱内平均confidence与支持率差计算。报告分箱/相同分值处理、有效样本数、涉及query数、缺失及unresolved覆盖、query整簇bootstrap区间。未知标签只作界限分析，不当作0；代数最坏/最好界限不是CI。

已有主结果仅87/1,008（8.63%）二元可判，来源是LLM标签，不可称全图事实校准。三模型200条样本富集了主Judge全部87条二元记录，不能把其43.5%覆盖率外推到1,008条。

跨Judge使用同一事实和confidence交集比较差异，同时报告各自覆盖变化；样本交集的差值0不证明全体稳定。11条无证据自动unresolved不当作三模型共识；三者请求模型同提供方、服务端快照未认证的限制保留。现有模型名按日志报告，不推断其架构独立性。

无原生confidence的方法校准为NA；不能补造baseline置信度或用答案F1充当confidence。可在相同可判定集合展示constant-0.5及域名数基线；由于支持类别高度占优，也应报告constant-1诊断，不能仅战胜0.5就称良好校准。任何从标签拟合的常数/映射须用开发集或留一query外拟合，不能原地拟合评估同一批；小样本局限如实说明。

## 7. 人工审核与案例：小范围但真实

复用400条既有盲审材料及来源快照；核查其抽样框后再解释代表性，不伪装成新N1样本。两位专家独立检查事实、引用、关系类型和scope，保留初始评分再仲裁。报告资质、任务说明、分层覆盖、三态混淆和IAA。富集分歧样本的结果不能直接外推总体。

39条三模型分歧可作为额外定向诊断，独立评分前不展示其他Judge/专家标签。Q61/Q64正文展示的实质关系须逐条核验；未审核的边删除强确认说法或明确未评估，不把研究范围扩成全产业链gold。

## 8. 可复用工具与未实现边界

已有 `judge` 接受标准facts/pages；**不会自动抽取视图B、设计公平样本或判断新旧标签是否可复用**，这些步骤需按上文保真适配。事实ID必须唯一，hash必须能追溯原report和page。现有`analyse`处理配对标签与coverage，`agreement`处理真实评分；三模型对比脚本是历史执行快照，不是可随处运行的一键入口。

以下是已有合规标签/真实评分准备好后的离线命令；路径为占位，输出必须是新路径，不包含模型调用：

```bash
V=reviewer_analysis.revision_v2
export FACTS='/实际冻结事实/facts.jsonl'
export LABELS='/对应版本最终标签/labels.jsonl'
export OUT='/新的本地输出目录'
python -m "$V" analyse --facts "$FACTS" --labels "$LABELS" \
  --methods Helicase --quadrants Q4 --fact-type edge \
  --bootstrap 2000 --out "$OUT/conditional_calibration"

export RATER_A='/实际独立专家A/ratings.csv'
export RATER_B='/实际独立专家B/ratings.csv'
python -m "$V" agreement --rater-a "$RATER_A" --rater-b "$RATER_B" \
  --out "$OUT/human_agreement.json"
```

`analyse`不是自动跨模型一致性工具，也不会修复label来源问题。若输出已存在，读取并核对即可，不为README更新而再生成。

交付：`sample_manifest.json`、`claim_inventory.jsonl`、`evidence_packets/`、`labels.jsonl`、`support_and_coverage.csv`、校准/一致性结果及`REMAINING_STATUS.md`。所有未做环节明确planned或blocked，不宣称完成所有reviewer要求。
