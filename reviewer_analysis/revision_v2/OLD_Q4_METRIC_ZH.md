# 旧 Q4 衡量什么：代码与新指标的区别

更新：2026-10-03（Europe/London）。本次仅公开方法说明和找到的旧代码快照；没有重跑模型或 agent，也没有改写原分数。

**旧结果应按旧指标解释：它衡量简短答案与文字 reference 的语义匹配，并用原生图密度构造关系质量代理量。新版全文参考图匹配衡量的是不同对象，不能把两者的数值差直接解释成方法性能下降。** 保留旧指标的历史名称不等于确认其实现无缺陷；新版结果同样有表示与匹配局限。

## 找到的代码

原本地路径为 `benchmark/eval_scpqa.py`，核心为 `evaluate_q4()`（427–508 行）。这份文件此前不在本公开检出中，现以独立快照保存：

- [旧脚本完整快照](reproducibility/historical_q4_metric_20261003/eval_scpqa.py#L427)
- [出处及校验记录](reproducibility/historical_q4_metric_20261003/provenance.json)
- SHA-256：`0d39bb5935a8e541b94d71de90d8862ac60095e9743b1a093f7e0da5dbca9403`

快照与找到的本地文件逐字一致。全部 140 条旧 Q4 归档的关系 P/R/F1 与其公式吻合，允许三位小数的舍入误差（绝对容差 0.0011）。这是数值一致性证据；尚未确定历史运行的精确源码 commit，也没有恢复当时每次 Judge 的原始匹配对。快照依赖原项目布局及模型配置，供阅读核对，不是建议重新执行的入口。

## 旧计算流程

### 1. 从报告提取直接答案

`extract_answer_from_report()` 取报告前 **8000 字符**，要求 LLM 输出 **1–3 句直接答案**。模型提取不可用时使用正文/结论段启发式回退。

预测答案和文字 reference 随后分别按逗号、分号切分。因此旧代码中的 entity 实际是答案文本片段，不一定是知识图谱实体。

### 2. 用语义匹配计算 Entity F1

```python
matches = llm_set_match(pred_items[:30], ref_items[:30], llm)
matched_pred = len({m[0] for m in matches})
matched_ref = len({m[1] for m in matches})
ep = matched_pred / len(pred_items) if pred_items else 0
er = matched_ref / len(ref_items) if ref_items else 0
ef1 = 2 * ep * er / (ep + er) if (ep + er) > 0 else 0
```

只向 Judge 传前 30 个片段，分母使用完整片段数量。`llm_set_match()` 接收返回的字符串对，但未验证字符串属于原输入集合，也未执行一对一约束。这是实现局限，不能据此认定所有旧匹配都正确。

### 3. 用实体分数和原生图密度推算 Relation F1

以下为旧代码原文：

```python
if kg_nodes and pred_relations:
    density = min(1.0, len(pred_relations) / max(len(kg_nodes), 1))
    rp = ef1 * (0.8 + 0.2 * density)
    rr = er * (0.8 + 0.2 * density)
else:
    rp, rr = ep * 0.85, er * 0.85
rf1 = 2 * rp * rr / (rp + rr) if (rp + rr) > 0 else 0
```

`kg_nodes` 是去重后的原生节点名称集合；`pred_relations` 是去重后的原生有向三元组集合。**这里没有逐条匹配 reference 关系。** 无有效原生节点/关系时，Relation F1 等于 Entity F1 的 0.85 倍；有原生图时走另一分支。在这批归档中，六个非 Helicase 方法走前者，Helicase 依据每题原生图情况分支。这并非统一的 reference-based relation evaluation。

### 4. 加权与汇总

```python
gf1 = 0.6 * ef1 + 0.4 * rf1
```

对各题的未舍入分数取算术平均，再保留三位小数。若存在 `final_memory`，旧单题 UCE 为 `abs((1 - final_memory) - gf1)`，再对有该值的题目平均；它也不等同于新版事实级 calibration。

## 新旧指标应分开报告

| 项目 | 旧 Q4 指标 | 新暂定 Q4 指标 |
|---|---|---|
| 预测对象 | LLM 提取的简短直接答案 | 全文统一抽取的节点、关系 |
| Reference | 原文字答案的逗号/分号片段 | 由原文字转换的 AI 审核参考图草稿 |
| 实体匹配 | 文本片段语义匹配 | 相同范围实体的一对一匹配 |
| 关系分数 | 实体分数与原生图密度的代理量 | 明确关系对，要求端点、方向及语义相容 |
| Reference 外内容 | 受答案压缩/切分影响 | 进入全文分母，可能降低 precision |
| 当前可解释性 | 历史答案匹配/图密度代理指标 | 条件于草稿参考及抽取、匹配规则的全文图指标 |

Helicase 的旧 Graph F1 为 0.853，新暂定值约 0.2097。两者不能作为同一测量尺度下的前后变化。旧版的答案语义接近程度仍是原本评价意图；新版分数不能替代或回溯重命名旧实验。

同时，旧版 Q73 存在大于 1 的分数；Q68 归档报告没有实质答案，旧分数却为 0.940。现有记录不足以区分历史 Judge 补答与报告/分数版本错配。新版则已发现 Q64 抽取主语错误及事实遗漏，Q70/Q77 有语义漏配疑点，品牌/SKU、公司/工厂和背景事实的表示也影响评分。**这些证据要求核对两套评估，不能预先认定旧排名正确或新排名正确。**

## 当前进度与下一步

140 份暂定 `match` 已完成，不再列为“没跑”。现在暂停增加模型调用和全量 agent 重跑，先离线对齐原文字 reference、参考图、报告抽取图与实际匹配对；对所有方法统一时间/市场、背景计分、实体粒度、关系方向及断言状态。真实作者确认、独立人审与严格预算重复实验仍未完成。

原始图、逐对匹配、报告全文与离线详细核对材料保存在本地 `reviewer_analysis/revision_v2/private/offline_evaluation_audit_v1/`，本次不公开这些私有材料。已有[暂定结果](reproducibility/provisional_graph_matching_20261003/README_ZH.md)保持原样；任何修正应使用新版本和可追溯修正记录，不能覆盖原结果或只为某一方法放宽规则。
