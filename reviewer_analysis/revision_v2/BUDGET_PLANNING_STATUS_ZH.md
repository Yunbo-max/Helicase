# GPT-5.5 两组预算控制实验：实施状态

更新时间：2026-10-04。**这是实现准备记录，不是实验结果。试运行 0/4，正式运行 0/80。**

范围遵循用户方案：仅 Q61–Q80，仅预算控制版 Helicase 与 Uniform-planning KG；所有模型角色使用同一 GPT-5.5，先做四次技术试运行，再冻结共享资源上限，执行两次独立重复。保留 KG、搜索、读页、历史和引用。

## 本次完成的离线组件

- `planning_budget.py`：并发安全的 token 预留；研究阶段不能使用最终回答预留额度；未知用量保留完整预留消耗，并与已知实际用量分开；搜索/读页的失败重试也需要占用调用额度。支持独占创建 JSONL 日志，避免旧运行被覆盖。
- `planning_control.py`：均匀选择不同有效目标，重复候选不增加选择概率；uniform 分支不读取评分回调；中性 KG/历史投影去除现有 schema 的 UQ 元数据，保留计划/未确认等事实限定。完成的是具体调查目标，允许同一概念的新调查角度。
- 同一文件中提供四次试运行和八十次正式运行的独立排程；同题两组相邻、顺序随机，每次有单独的运行标识和种子；只传问题字段，不向研究 agent 传 reference。
- `planning_statistics.py`：先平均每题两次 F1，再在 20 道题上配对 bootstrap；另报两次运行均值及样本标准差。必须提供全部 80 条正式评分，不能静默删除失败。每次分析对应一个固定评委/评分协议，不能把多个评委平均后的 P/R 当成一次原始匹配。

新增 23 项组件测试通过。当前隔离工作目录全套软件测试 **167 passed, 1 skipped**。这些测试没有调用模型，没有形成新实验结果。

## 尚未接通，不能提前宣称完成

1. GPT-5.5 真实后端和 provider 强制输出上限、完整输入计数、失败用量/重试计量。现有 Codex CLI 访问可用性来自此前评估，不能据此推断具有严格 token 上限。
2. 原生 planner/orchestrator：两组共用中性候选生成；Full 使用原 UQ reduction/cost 选择一个调查目标，Uniform 均匀选目标；两组统一绕过动态并行选择，使用不依赖 UQ 的停止规则。原 `repeat` 命令仍不可用于冒充本实验。
3. 在实际模型、Serper、页面及其 fallback 调用之前接入预留。需要检查 coding 执行等旁路。原读页的可选非 GPT OCR 两组统一关闭。
4. 四次试运行及其有限安全上限、正式预算冻结、80 次执行、新输出统一评分和最终结果表。

本次检查时，进程及已检查的项目配置没有非空 `OPENAI_API_KEY`；搜索/Jina key 存在，但尚未在线验证。已向用户询问可用 GPT-5.5 API 配置的本地路径。**无需在聊天里发送密钥。** 后端条件解决后，仍须完成以上接线与试运行，不是填 key 就可以直接跑现有 `repeat`。

中性投影只覆盖已检查的字段约定；新增 UQ 字段或自由文本中混入控制元数据时，必须补充实际 prompt 的不泄漏测试，不能把组件测试当成全链路证明。

## 复验说明

原默认 Conda Python 在 pytest 导入 `readline` 时崩溃；本次使用已有 uv Python 3.12 加载已安装 pytest 完成基线及新增测试，没有修改全局 Python 环境：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  /Users/yunbo/.local/share/uv/python/cpython-3.12.2-macos-aarch64-none/bin/python3.12 \
  -c 'import sys; sys.path.append("/Users/yunbo/miniforge3/lib/python3.12/site-packages"); import pytest; raise SystemExit(pytest.main(["-q"]))'
```

独立分支：`experiment/gpt55-budget-planning`，工作目录 `/private/tmp/helicase-budget-planning-20261004`。尚未合并或发布这些准备组件。旧报告、旧评分和本地核心算法修改保持原状。
