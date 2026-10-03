# Q4暂定参考图匹配公开记录（2026-10-03，Europe/London）

已完成 **7系统×20题=140份暂定匹配**，使用已冻结的统一报告抽取图。参考图由GPT-5.5从原20份文字答案转换、经过记录在案的离线AI修订，**没有作者完整性确认，不能当作正式gold实验结论**。

[结果报告](RESULTS_ZH.md) · [140份逐题数值](per_query_scores.csv) · [均值、CI及六组配对比较](summary.json) · [匹配审计](audit.json)

Helicase的暂定Graph F1为0.2097；与另外六个系统的配对差值95%置信区间均跨0，本轮不能证明明确优势。Graph F1=0.6×Entity F1+0.4×Relation F1，均值按20题macro计算；2000次query bootstrap固定seed20261003，只反映固定参考及matcher条件下的题目差异。

## 实际运行与限制

- 参考草稿：20次GPT-5.5 CLI调用，435节点、496关系；148条离线修订记录包含引文上下文扩展，不等于148个独立事实错误。[reference_draft_audit.json](reference_draft_audit.json)是草稿完成时的历史快照，里面的match=0不代表后来没有匹配。
- 匹配：140次初始调用、4次结构失败修复，共144次CLI调用。DeepSeek修复2次、Helicase和Qwen3-235B各1次。仅结构无效输出可修复，每项最多一次、全局20次上限；未按分数择优，没有重复评估成功项。
- 两个阶段合计164次CLI调用；CLI内部重试和HTTP/账单计数未独立测量。实际请求gpt-5.5、medium reasoning，服务端模型快照未获认证。
- 140份最终结果、原失败及修复原文、完整提示词与用量已在本机逐项审计。原参考、140份预测图和受保护原文件哈希未变；没有重跑extract、主事实Judge、网页抓取或agent重复。
- 20题统一时间/市场范围仍未冻结；公司级采购不等于具体产品供货，Q80封装测试/制程原文仍有歧义。原文引文一致性不等于事实真实或参考完整；unmatched不等于世界中错误。参考和预测图的粒度与覆盖也影响分数。
- 原始数据、作者审核表、完整图/匹配对、模型事件、登录配置和密钥未公开。本次CSV仅含系统、题号、计数和数值；每行保留暂定状态、作者未确认及是否修复标志。

## 执行代码快照

两个子目录中的8个Python文件与实际执行文件逐字一致，见[source_provenance.json](source_provenance.json)。它们供检查运行逻辑，**不是可直接执行的一键重现实验包**。

原运行布局为`reviewer_analysis/revision_v2/private/reference_draft_v1/`及`private/provisional_match_v1/`。相对路径、原机`/tmp/helicase_revision_v2_before.json`、冻结protocol/source hashes和原始调用记录均有依赖。本公开目录没有这些私有输入，目录深度也不同；不要直接执行`run_draft.py`或`continue_run.py`，不要在原完成目录重跑。迁移环境须重新定义路径及版本，不能宣称恢复了原运行身份。

`analyse_v2.py`合并有效初始结果与修复结果，并严格拒绝缺题和非法匹配。原私有`matches/results.jsonl`只包含136份首次成功结果；这里的`per_query_scores.csv`包含完整140份最终结果。

测试仅用合成数据和替代CLI，不调用真实模型。在仓库根目录运行：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p no:capture \
  reviewer_analysis/revision_v2/tests \
  reviewer_analysis/revision_v2/reproducibility
```

本地相关套件88项通过（3.87秒），见[private_software_verification.json](private_software_verification.json)。公开检出的验证结果另见[VALIDATION.md](../../VALIDATION.md)，软件测试不构成真实模型或人工真值证据。

完整研究仍缺作者确认gold、真实独立专家标注、独立agent重复和严格预算对照；本次没有启动240次重跑。
