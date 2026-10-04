# GPT-5.5 两组真实运行说明

本批仅包含预算控制版 Helicase（`full`）与保留 KG 的 Uniform-planning（`uniform`）。Q61–Q80，每组两次全新执行，共 80 次；另有 Q61/Q73 × 两组的四次技术试运行。原 SCQA、历史答案和 Q3 不修改。

## 用户确认后的预算口径

2026-10-04 用户明确选择：使用现有 Codex GPT-5.5 跑完，统一工具和调用上限，token 仅实测、非严格匹配。

- 所有模型角色都请求 `gpt-5.5`、medium reasoning；CLI 关闭工具，实际搜索/读页由原生执行器完成。
- 模型上限的单位是 **CLI 调用次数**，不是独立测得的内部 HTTP 请求数。CLI 请求及流重试配置为 0，但不把这项设置当成独立的后端调用证明。
- Serper 请求与读页 HTTP 尝试在实际发送前占用额度；失败、重试、重定向和 Jina fallback 都计数。
- 两组相同固定 `n=2`。少于两个不同查询会记录错误，不能无声退回一路。
- 两组共用中性候选生成。Full 用原预计 UQ 降低量/成本选择，Uniform 对不同目标均匀抽样；图更新和 UQ 计算保留在两组。
- 停止依据是共享迭代上限、调用/检索额度或没有有效候选；UQ 不参与停止。最终回答固定预留一次模型调用。
- 两组都关闭原读页中的 Playwright fallback 和其他模型 OCR，以保证已审计的 HTTP 路径可计量。这是共享设置下的规划对照，不是完整默认系统组件消融。

## 四次技术试运行的安全上限

每次最多 96 次模型 CLI 调用（含一次最终回答）、36 次 Serper 请求、60 次读页 HTTP 尝试、3 次规划迭代。固定两路检索、每次搜索最多取 5 条结果，Reader 并发 4，PreFilter 并发 2。

四次试运行全部经过功能检查后，对各资源取四次中的最大实测值 × 1.25，并向上取到 5 的整数倍，作为两组共享的正式上限；最低为 20 次模型调用、5 次搜索、5 次读页。规则在试运行评分之前确定，不查看谁的 F1 更高。最终回答一次、3 次迭代、n=2 不变。

`freeze-formal` 会拒绝缺少引用/图边、模型调用失败、原生动作失败或控制错误的试运行。技术试运行中，原生搜索器会把正常调用上限拒绝包装为内部搜索错误，因此需要查看原始日志作功能核对：只有确认失败全部来自预算耗尽、没有请求失败或控制错误、计数未超限且最终预留回答成功时，才可另存带原输出和日志哈希的功能审核记录，使用原规则推导正式上限。原 `partial` 状态不改成 `complete`，原输出不重跑；审核路径和审核脚本哈希写入正式配置。正式运行中所有失败状态保留；发生模型通道或控制层故障时，批次停止，排查后只继续尚未开始的任务，不静默重跑失败题。

## 本地命令

以下依赖目录是本机已验证环境；其他机器应自行安装项目依赖与 sentence-transformers。`SERPER_API_KEY` 在项目 `.env` 中设置，密钥不进入冻结配置或公开结果。

```bash
cd /private/tmp/helicase-budget-planning-20261004
EXPERIMENT_PY=/Users/yunbo/.local/share/uv/python/cpython-3.12.2-macos-aarch64-none/bin/python3.12
EXPERIMENT_ROOT=/Users/yunbo/Documents/GitHub/Data_provider/Helicase/reviewer_analysis/revision_v2/private/planning_gpt55_v1
export HELICASE_ENV_FILE=/Users/yunbo/Documents/GitHub/Data_provider/Helicase/.env
export HELICASE_DEPENDENCY_PATHS="$EXPERIMENT_ROOT/runtime_dependencies:/Users/yunbo/Documents/GitHub/Data_provider/Helicase/.deps312:/Users/yunbo/miniforge3/lib/python3.12/site-packages"

# 新建冻结目录；已有 freeze.json 时不覆盖。
"$EXPERIMENT_PY" -m reviewer_analysis.revision_v2.planning_run prepare \
  --out "$EXPERIMENT_ROOT" \
  --dataset /Users/yunbo/Documents/GitHub/Data_provider/Helicase/benchmark/scpqa.jsonl \
  --runtime-root /Users/yunbo/Documents/GitHub/Data_provider/Helicase \
  --backend-root /Users/yunbo/Documents/GitHub/Data_provider

"$EXPERIMENT_PY" -m reviewer_analysis.revision_v2.planning_run pilot --out "$EXPERIMENT_ROOT" --max-jobs 4
"$EXPERIMENT_PY" -m reviewer_analysis.revision_v2.planning_run freeze-formal --out "$EXPERIMENT_ROOT"
"$EXPERIMENT_PY" -m reviewer_analysis.revision_v2.planning_run formal --out "$EXPERIMENT_ROOT" --max-jobs 80
```

每次独立 worker 从冻结源码创建空 KG、新历史与新进程内缓存。`status.json`、`calls.json`、`retrieval.jsonl`、规划选择、逐轮图快照、报告与原始模型响应留在对应 `phase/repeat/question/method` 目录。题目文件只含问题，不含 reference、答案或标准答案来源。

## 结果口径

新报告使用 `blind_direct_answers_v4` 的抽取、粒度规范化与匹配协议，对相同 `scpqa` reference cards 评分。抽取不看 reference；统一评分 GPT-5.5 的调用量与研究 agent 的调用量分开。历史预测答案项和历史分数不作为新实验输出。

主表报告 Answer P/R/F1、实际 token（含未知用量缺失标记）、模型调用次数、搜索和读页尝试。先对每题的两次 F1 求平均，再对 20 道题作配对 bootstrap；另报两次整体均值和样本标准差。两个重复不足以证明充分稳定性。保留 V4 对 epistemic admission 的范围限制，不在看到结果后修改分母。


## 80 次结束后的统一评分

```bash
EVALUATION_ROOT="$EXPERIMENT_ROOT/evaluation"
"$EXPERIMENT_PY" -m reviewer_analysis.revision_v2.planning_evaluation prepare \
  --experiment "$EXPERIMENT_ROOT" --out "$EVALUATION_ROOT"
"$EXPERIMENT_PY" -m reviewer_analysis.revision_v2.planning_evaluation execute \
  --out "$EVALUATION_ROOT" --execute
```

结果写入 `per_execution.csv`、`per_query.csv`、`summary.json` 与 `summary_table.md`。没有报告的正式运行保留为零分；评估调用失败则保留失败记录并停止，不自动重试或当作有效零分。成功缓存不重复调用。
