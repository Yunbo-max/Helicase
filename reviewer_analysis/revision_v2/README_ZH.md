# Helicase / IJPR 268226721：补实验运行包 v2

这是一组独立工具，放在 `reviewer_analysis/revision_v2/`。**不修改 `helicase/`、`helix_core/`、旧结果或旧分析脚本。** Python 3.10+。本包不含你的未公开运行源码、密钥、原始结果或真实 gold graphs。

**先复用原 SCQA 和已保存结果。** 此工具包不要求更换数据集，也不会自动启动全量重跑。先运行离线检查，再按缺少的证据选择评估或重复运行。

## 先分清：什么已经可运行，什么不能只靠一个 key 解决

| 工作 | 本包入口 | 还需要什么 | 是否重新运行主 agent |
|---|---|---|---|
| 旧结果导入、非法分数与引用解析检查 | `prepare` | 你原来的 `results.zip` | 否，无 API |
| 所有方法按同一报告抽取视图重新评估 | `extract` → `match` | judge API + 完整、版本化 reference graphs | 否 |
| 引文页面文本收集 | `pages` | 网络；Jina key 可选 | 否；只读取已引用 URL，不用 Serper 搜索 |
| 事实级证据判定、ECE/Brier/可靠性图/查询聚类 CI | `judge` → `analyse` | 已保存页面 + judge API；强验证还需人类标签 | 否 |
| 400 条原始 KG 边的盲审与 IAA | `human-forms` → 两人独立填写 → `agreement` | 真实专家，不是 LLM 代签 | 否 |
| Helicase 固定配置下独立重复 | `repeat --variants full` | **完整本地 `helicase` 和 `helix_core`** + LLM/Serper | 是 |
| 固定 n=1 功能控制 | `repeat --variants full,search_n1` | 同上；可以只跑 Q4 | 是 |
| 同模型、同实际 token/tool cap 的 Full/no-UQ/ReAct/ToT 比较 | `EXPERIMENT_PROTOCOL.md` | 原 baseline/no-UQ 运行入口及可观测后端调用计数 | **本包没有伪装成已接通** |
| 真 held-out | 使用新 question manifest 后 `repeat` | 冻结后新题、独立标注与时间证据，或既有未用测试集历史 | 是，不能随机拆旧 80 题冒充 |

`extract/match` 是**新定义的 v2 evaluator**，不是找回了历史 evaluator。优先找回原 evaluator/gold。无法找回时，统一使用并披露新协议，重算所有比较；不要把新分数冒充对旧数字的逐位复现。

## 1. 安装与密钥

在本地 `Helicase` 仓库更新代码后，使用原来可运行的 Python 环境：

```bash
git pull --ff-only origin main
python -m pip install -r reviewer_analysis/revision_v2/requirements.txt
mkdir -p reviewer_analysis/revision_v2/private
cp reviewer_analysis/revision_v2/.env.example reviewer_analysis/revision_v2/private/.env
```

编辑 `private/.env`。包内 `.gitignore` 会排除整个 `private/`。不要把 `results.zip`、页面原文或实际 key 放到待提交代码目录之外的未忽略路径。

**沿用原来的 SiliconFlow 配置时，填 `SILICONFLOW_API_KEY`，不是另买一个所谓 Qwen 专属 key。** Qwen 是模型，SiliconFlow 是你调用模型的服务商。`SERPER_API_KEY` 用于原 agent 搜索。Jina Reader 基础读取可无 key，但批量限速和你原 backend 的配置可能要求 `JINA_API_KEY`。Native backend 的具体要求仍须在本地核实。

重新评分使用 `REVIEW_JUDGE_BASE_URL`、`REVIEW_JUDGE_MODEL`、`REVIEW_JUDGE_KEY_ENV`。同一个 SiliconFlow 账户可以作为这个客户端的凭证来源。模型 ID 必须填写你账户当前可用的准确 ID。`.env.example` 的 native IDs 来自历史源码，**没有通过实时 API 验证仍可用**。不要换成“最新模型”后与旧运行合并成相同配置。

阿里云 Model Studio 的 key 与 SiliconFlow key 不通用。选择阿里云时，judge 使用相应地域的兼容 endpoint，并设置 `REVIEW_JUDGE_KEY_ENV=DASHSCOPE_API_KEY`。native 工厂虽有 provider 自动识别，缺失的 `helix_core` 适配器未在这里实测。

建议 shell 变量（后面的命令在同一个 terminal 执行）：

```bash
V=reviewer_analysis.revision_v2
P=reviewer_analysis/revision_v2/private
ENVFILE="$P/.env"
```

## 2. 先执行完全离线检查

```bash
python -m "$V" prepare --archive /你的路径/results.zip --out "$P/archive_v2"
python -m "$V" --env-file "$ENVFILE" doctor --purpose judge
```

`prepare` 只读取 7 个主实验 `scpqa_*.jsonl` 文件以及对应汇总评估文件，只取原 SCQA 的 1–80 号问题。它不解压任意 ZIP 路径；忽略 Iran、其他案例、浏览器版 deep-research 结果和未知成员。7 个系统逐题问题文本不一致时直接报错。

输出：`records.jsonl`、`questions.jsonl`（仅问题，不含 gold）、`facts.jsonl`、`source_urls.jsonl`、`audit.json`。保存输入和成员 SHA-256。**不把汇总 precision、截断 reference 字符串变成 gold graph；不 clip 非法评分。**

导入在本次真实归档上已运行：7 × 80 = 560 个记录；Helicase Q4 1,008 条边，其中 992 带引用 ID、969 可解析到至少一个已保存 URL。这只是本地引用解析，不是页面支持率。

## 3. Q4 统一重新评分（优先级最高）

### 3.1 报告抽取：全部方法走同一条路线

```bash
# 无 --execute：只显示计划，不调用 API。
python -m "$V" --env-file "$ENVFILE" extract \
  --records "$P/archive_v2/records.jsonl" --quadrants Q4 \
  --out "$P/extract_v2" --max-calls 2

# 抽取图通常比事实标签长，给足输出上限。这里只是上限，不是费用报价。
REVIEW_JUDGE_MAX_TOKENS=16384 python -m "$V" --env-file "$ENVFILE" extract \
  --records "$P/archive_v2/records.jsonl" --quadrants Q4 \
  --out "$P/extract_v2" --max-calls 2 --execute
```

检查 `extract_v2/items/` 的原始返回、图和引用原报告的逐字片段。输出被截断、JSON 错误、伪造片段或非法图都会报错并停止，不拿残缺返回评分。确认环境正确后，**保持同一输入和设置**再次运行、将 `--max-calls` 提高到 140，可完成这批 20 × 7 报告。已有成功项不重付费；失败项保留，不自动尝试直到得到好分数。

模型不见 method 名称、gold 或 native confidence。新图不继承原生节点/边 uncertainty。**统一报告评分与原生边校准是两个不同对象，不能凭相似名字把 confidence 偷接到新图。**

### 3.2 提供真正 reference graph，再匹配计数

创建本地 `private/reference_q4.jsonl`。每行结构：

```json
{"query_id":"Q61","reference_version":"作者确认的真实版本","scope":{"as_of":null,"market":null},"graph":{"nodes":[{"id":"g1","name":"真实参考实体","node_type":"product"}],"edges":[]}}
```

上面仅解释 schema，**不是 Q61 的真实 gold，不得复制这个示例去评分**。每条关系使用 `id/source_id/target_id/relation_type`；建议保留 `evidence_status` 和时间/地域元数据。禁止同一图中的重复 ID、重复三元组和悬空端点。人工标注应覆盖实体别名及引用来源，并保存仲裁前记录。

```bash
python -m "$V" --env-file "$ENVFILE" match \
  --predictions "$P/extract_v2/results.jsonl" \
  --reference "$P/reference_q4.jsonl" \
  --out "$P/matching_v2" --max-calls 2 --execute
```

LLM 只给匹配对，Python 根据**一对一映射**、端点方向及真实分母计算 E-F1、R-F1、0.6 E-F1 + 0.4 R-F1。未知 ID、多对一和反向边映射直接报错。两个图在某类同时为空时该类指标未定义，不虚填完美分数。语义等价判断仍须抽样人工核查。

匹配得到的是 **closed-reference graph F1**。Unmatched 不等于世界中错误。不要将它直接作为开放世界 truth label。

配对置信区间：

```bash
python -m "$V" paired --scores "$P/matching_v2/results.jsonl" \
  --method-a Helicase --method-b ReAct --expected-queries "$P/reference_q4.jsonl" --out "$P/Helicase_vs_ReAct.json"
```

函数先在 query 内平均重复运行，再 bootstrap query。缺失 query 会报错。运行数按 query 输出，避免把所有重复当成独立问题。此 CI 不能修复评分定义错误，也不解决跨方法预算混杂。

## 4. 原生边的事实级标签与校准

先读已经保存的 URL，不做新的 Serper 搜索：

```bash
python -m "$V" --env-file "$ENVFILE" pages \
  --facts "$P/archive_v2/facts.jsonl" --methods Helicase --quadrants Q4 \
  --out "$P/cited_pages" --max-pages 20 --execute
```

原始页面、完整文本 hash、抓取时间和失败记录都缓存。再次执行可继续读取其余 URL；改变上限不会删除缓存。失败页面不自动重试。**当前重新读取不是原运行时的网页快照**；不要据此声称历史截止日前已经有这段内容。已有历史快照更好，按相同 `pages.jsonl` schema 输入即可。

```bash
python -m "$V" --env-file "$ENVFILE" judge \
  --facts "$P/archive_v2/facts.jsonl" --methods Helicase --quadrants Q4 --fact-type edge \
  --pages "$P/cited_pages/pages.jsonl" --assessor primary_judge \
  --out "$P/fact_judge_primary" --max-calls 10 --execute

python -m "$V" analyse \
  --facts "$P/archive_v2/facts.jsonl" --methods Helicase --quadrants Q4 --fact-type edge \
  --labels "$P/fact_judge_primary/labels.jsonl" \
  --out "$P/calibration_primary" --bootstrap 2000
```

`truth_status` 为 supported / contradicted / unresolved。前两种必须有输入页面中的逐字引文；校验引文存在不等于证明世界事实正确。judge 不见 method 和 confidence。默认最多展示 4 个可用来源、每个 8,000 字符，截断和未展示来源数量有记录。**抽取不充分的 unsupported 不是 contradicted；缺页面不会被判 false。**

精确配对后的 ECE、自适应 ECE（不拆相同 confidence）、Brier、可靠性 SVG/PNG、query-cluster bootstrap CI、LaTeX 表和 CSV 会输出。同时报告 unresolved、missing labels、无 confidence 的数量和覆盖率。另提供缺失标签情况下 Brier 的代数上下界，以及固定 0.5 / domain-count 简单分数基线。来源域不同不等于独立。

**这首先是相对于 LLM 证据判定的诊断，不等于独立人类事实校准。** 校准主要分析原生边。node 模式只评价身份/类型，不保证验证该节点所有属性；它是单列的 score-scope 诊断，不能与 edge 混称同一事实级实验。

新增页面后不要覆盖已有 judge 目录。新页面文件 hash 会改变；使用例如 `fact_judge_primary_v2` 保存一个新的评估版本。替代 judge 使用同一批快照和事实、不同的实际模型（最好不同家族），并使用新的 assessor 名称和输出目录；仅换 key 不构成替代 judge。

## 5. 人工审核：必须是真实独立标注

```bash
python -m "$V" human-forms --facts "$P/archive_v2/facts.jsonl" \
  --out "$P/human_audit" --sample 400
```

默认包括 Q61/Q64 的全部原生边，再对其余方法/置信度分层抽样。提供两张**空白、看不到 method/confidence 的** CSV。两名专家分别填写，不提前互看。`PRIVATE_mapping.jsonl` 只给组织审核的人，不给盲审者。

该归档中 baseline 原生 KG 为空，所以这份原生图审核主要覆盖 Helicase；不能宣称已经审核了所有 baseline。后续应对统一抽取的 baseline claims 配对具体引用再做人审。

样本含案例全量与分层富集，并非简单随机抽样。IAA 可直接报告；事实支持率和校准只能按其抽样设计解释，不把未加权的富集样本当全体事实总体。

```bash
python -m "$V" agreement --rater-a "$P/human_audit/rater_a.csv" \
  --rater-b "$P/human_audit/rater_b.csv" --out "$P/human_audit/iaa.json"
python -m "$V" human-labels --ratings "$P/human_audit/rater_a.csv" \
  --mapping "$P/human_audit/PRIVATE_mapping.jsonl" --assessor expert_a \
  --out "$P/human_audit/expert_a_labels.jsonl"
```

IAA 在仲裁前计算。保存所有分歧，第三人仲裁另建文件；不覆盖最初两份评分。空白意味着未标，不自动算 unresolved，更不能填成 0。标注者人数、资质、日期、scope 和仲裁说明仍由作者提供。

## 6. 重复运行原系统：完整本地运行环境上操作

`/你的完整运行工程` 必须可导入 `helicase`。`--backend-root` 指包含 `helix_core` 的父目录；两者同根时省略。公共论文仓库或那份符号链接式 `helix_core.zip` 不能替代源码。

```bash
python -m "$V" --env-file "$ENVFILE" doctor --purpose agent \
  --runtime-root /你的完整运行工程 --backend-root /包含helix_core的父目录

# 先运行两个环境 smoke queries，不计为独立最终测试集。
python -m "$V" --env-file "$ENVFILE" repeat \
  --questions "$P/archive_v2/questions.jsonl" \
  --runtime-root /你的完整运行工程 --backend-root /包含helix_core的父目录 \
  --ids 1,21 --runs 1 --variants full --dataset-role pilot \
  --out "$P/pilot_native" --max-jobs 2 --wall-seconds 3600 --execute
```

然后检查每个 query 的 `worker.log`、`native_output.json`、`resolved_config.json` 和 `status.json`。原 backend 有时在内部失败后仍返回部分图；`native_returned` 只表示返回了数据，不表示搜索完整或答案正确。不能把失败静默剔除。

以下是选择全量重复时的命令，不是默认启动任务。当前 runner **逐题串行**：`--max-jobs` 是本次最多启动次数，不是并发数；`--wall-seconds` 是每次执行的超时上限。

全量重复（80 × 3 = 240 次原系统执行）：

```bash
python -m "$V" --env-file "$ENVFILE" repeat \
  --questions "$P/archive_v2/questions.jsonl" \
  --runtime-root /你的完整运行工程 --backend-root /包含helix_core的父目录 \
  --runs 3 --variants full --out "$P/repeats_native" \
  --max-jobs 240 --wall-seconds 7200 --execute
```

每次运行是新进程、新图、新随机种子与独立输出。存 `freeze.json`、源码 hash、模型与配置和顺序；更改配置后不能覆盖继续。provider 未保证 seed 控制，seed 不意味着 API 确定性。按原代码保留自然停止，Q1–Q3 最多10轮、Q4最多20轮。Neo4j 明确禁用，避免额外写入外部数据库。

恢复是继续**尚未开始的 query/run**，不是把上个 run 的 checkpoint 搬到下一次。失败任务不会自动重试；保留并诊断，然后另开版本或明确记录替代执行。终止进程/配额耗尽也必须纳入 failure accounting。

Q4 的 n=1 功能控制可用单独输出目录。若同一配置的 Full 已运行，复用其结果，只运行 `--variants search_n1 --max-jobs 60`，不要重复付费运行 Full：

```bash
python -m "$V" --env-file "$ENVFILE" repeat \
  --questions "$P/archive_v2/questions.jsonl" \
  --runtime-root /你的完整运行工程 --backend-root /包含helix_core的父目录 \
  --ids 61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80 \
  --runs 3 --variants full,search_n1 --out "$P/q4_n1_control" --max-jobs 120 --execute
```

`search_n1` 只将原配置 `n_min=n_max=1`。它不是“移除 search agent”，不是“关闭 UQ”，也不是预算匹配。`--single-model` 可将所有已暴露角色设成 `SILICON_MODEL`，但完整 backend 的潜在额外调用仍需审计。

**这版 repeat 没有伪称能严格计量/拦截隐藏 backend 内全部 token 或 Serper 调用。** 它只给 iteration 和 wall-clock 限制。因此不能把这些运行写成 reviewer 要求的 matched-token/tool comparison。原来的 ReAct/ToT/no-UQ 运行脚本不在提供的源码中；本包拒绝杜撰这三个方法或用一个同名 flag 假装实现。

新结果可重新生成原生 fact 表：

```bash
python -m "$V" facts --records "$P/repeats_native/records.jsonl" --out "$P/repeats_native/facts.jsonl"
```

## 7. 真 held-out 的边界

先冻结代码、prompts、模型、预算与评估协议，再构建作者之前没用于开发的新 query/reference 文件。建议另做20题、每象限5题；这个数量是补实验建议，不是已经有这样的数据。记录日期、标注过程和去重检查。

`repeat --questions 真实新文件 --dataset-role new_holdout` 支持新 query IDs，但 flag **不能证明**真的 held out。若已有真正未用过的测试集，先提供开发历史，而不必无理由浪费已有数据。

## 8. GitHub 提交与验证

本目录是独立补评估工具，不包含未公开的核心 runtime、原始数据或密钥。更新后先检查软件测试和命令入口：

```bash
python -m pytest -q
python -m reviewer_analysis.revision_v2 --help
```

不要提交 `private/.env`、原始结果、网页全文或未授权公开的 runtime。GitHub 提交成功与新实验运行成功是两个不同状态。

若需完整工程复现，按你已可工作的环境安装原工程依赖；本包 requirements 只安装新增分析工具，不伪造或替换缺失的 `helix_core`。本地单元/模拟测试通过不等于真实API、真实运行时间、预算公平或新实验结果已验证。

Ctrl-C 会终止当前付费子进程并记录 interrupted。出现已知的配额/规划失败日志时标记 needs_review 并停止批次；这只是保守的异常检查，不保证识别后端所有部分失败。
