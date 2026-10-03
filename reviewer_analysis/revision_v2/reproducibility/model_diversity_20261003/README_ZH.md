# 三模型补评估公开汇总（2026-10-03，Europe/London）

本轮在同一冻结200条上完成GPT-5.5、GPT-5.6-Sol、GPT-5.6-Terra三模型比较；提示词、证据顺序、scope及4来源/8000字符限制保持一致，均请求medium reasoning。

每个新增Judge处理200条：189次真实CLI调用，11条无可用证据、零调用并记录unresolved。先2条试运行，再继续剩余项。

| 模型对 | 一致/实际双调用 | 一致率 |
|---|---:|---:|
| GPT-5.5 / GPT-5.6-Sol | 169/189 | 89.42% |
| GPT-5.5 / GPT-5.6-Terra | 157/189 | 83.07% |
| GPT-5.6-Sol / GPT-5.6-Terra | 162/189 | 85.71% |

189条三者实际调用样本中，150条完全一致（79.37%）；38条两同一异，1条三者各异，共39条分歧。含11条机械unresolved时，200条中161条三者一致（80.5%）；正文优先使用排除机械项的比例。没有把多数票当真值，也没有改写主标签。

| Judge | supported | contradicted | unresolved（含11条无证据） |
|---|---:|---:|---:|
| GPT-5.5 | 85 | 2 | 113 |
| GPT-5.6-Sol | 69 | 2 | 129 |
| GPT-5.6-Terra | 65 | 2 | 133 |

这是按原主Judge标签富集的诊断样本：保留全部85 supported、2 contradicted，从921 unresolved中固定抽113条，seed=20261002。不能将样本一致率直接外推到1008条总体。仅2条原contradicted也不足以支持稳定负类结论。

[comparison_summary.json](comparison_summary.json)包含三标签组合、按原主Judge分层的一致性、每对模型的共同二元交集Brier/ECE差异、2000次query整簇bootstrap及各模型覆盖率。差值使用相同事实及原存储置信度；各自不同覆盖子集上的条件指标不能直接解释为性能高低。此次公开汇总删除了逐事实ID，原始结果未修改。

[audit_summary.json](audit_summary.json)记录完整性检查及CLI用量：两个新增Judge共378次成功调用；另有一次历史GPT6请求被当前ChatGPT通道拒绝。总379次CLI调用不等于HTTP请求数或账单计数。189份第三模型提示词逐字核对；前两轮1542份相关文件、1008份主结果和9份受保护原文件哈希保持不变。

三者是OpenAI通道上的不同请求模型ID。CLI不返回服务端模型快照，不能据此声称独立供应商、不同训练架构或人工验证。最初gpt-6-sol被服务端拒绝，后按实际CLI目录选用Sol/Terra；没有以GPT6名称报告其他模型结果。

## 代码快照与重现范围

此目录的11个Python文件逐字复制自完成本次运行的私有工作目录，来源hash见[source_provenance.json](source_provenance.json)。它们用于检查实际执行逻辑，不是已打包好数据的一键重跑入口。

- 相对布局对应本地`private/remaining_v1/`，运行器要求已经冻结的`secondary_sample/`、原主评估`../gpt55_q4_batch_v1/`、相应模型目录文件及历史哈希清单。
- 审计还需要原机的`/tmp/helicase_revision_v2_before.json`以及历史protocol中记录的源路径。这里保留实际执行代码，未为了公开改变已冻结运行配置。
- 原protocol含私有绝对路径和运行代码hash，直接从本目录执行不能保证恢复原批次。不要在原完成目录重跑模型或覆盖已有结果。换环境须另外定义版本和路径映射；没有这些私有输入时不能独立重建该实验。
- 不公开`.env`、登录状态、完整来源文本、原始模型事件/输出、逐条标签或人审材料。公开的是汇总和代码快照；原始记录仍保存在作者本地。
- 这些测试使用合成CLI响应和合成标签，测试不会调用真实模型。

在仓库根目录运行公共测试及此快照测试：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p no:capture   reviewer_analysis/revision_v2/tests   reviewer_analysis/revision_v2/reproducibility/model_diversity_20261003
```

本地私有完整套件此前110 passed（4.41秒），含一个未公开的旧GPT6失败通道测试组及私有主批处理测试。公开检出的测试数量另行记录在[VALIDATION.md](../../VALIDATION.md)，不能把合成软件测试当作实际模型运行证据。

仍缺作者确认的完整Q4参考图、真实独立专家评分、agent重复和严格预算对照；本轮没有启动240次重跑，也没有完成整个研究实验。
