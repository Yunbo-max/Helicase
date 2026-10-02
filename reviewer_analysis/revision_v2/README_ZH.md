# Helicase / IJPR 268226721：只做剩余任务

**先读本页，不要再从完整指南的 `prepare` 开始重跑。保留原 SCQA、原 reference、已完成输出和 Helicase 核心算法。**

[完整命令手册（保留原版）](README_FULL_ZH.md) · [本次已报告的运行记录](VALIDATION.md) · [实验协议](EXPERIMENT_PROTOCOL.md)

本页以提交 `83d7f07b269fb7d5b11d6fb7c4c5e9846bb29c3f` 的 `VALIDATION.md` 为依据。详细新结果仍在你的本地 `private/`，未随 GitHub 提交公开。本页是接续工作清单，不是再次独立核验了那些本地原始结果。

## 0. 哪些已完成，不再原样运行

| 阶段 | 运行记录中的状态 | 接下来怎么做 |
|---|---|---|
| 旧结果导入 | 7 个方法 × 80 题；原始文件保留 | 复用现有 `records.jsonl` / `facts.jsonl` |
| Q4 `extract` | 140/140 份通过检查的报告图；修复过程保留 | 使用最终已验收的抽取结果，不重新抽取 |
| `pages` | 484 个 URL 都有结果；426 可用，58 失败或受阻 | 复用经筛查的快照，不全量重抓 |
| 主 Judge | 1,008 条边：85 supported、2 contradicted、921 unresolved | 复用最终标签、逐项记录和 manifest |
| `analyse` | 87 条二元可判边；覆盖率 8.63%，15 个 query；Brier 0.052989，ECE 0.157471 | 保留为**可判定子集的条件校准**，不是全图校准 |
| 人工材料 | 400 条空白独立评分表已生成 | 交给真实专家填写，不重新生成相同表 |

**新标签并非说明旧 SCQA 无效。未判定（unresolved）不等于错误；图结构或引文字符串通过检查，也不等于世界事实已经验证。**

只安排下面三项接续工作：

1. **原 Q4 reference 接入 → `match` → 统计。** 没有完整原 reference 时先暂停这一项，不重新做数据集，不让模型从预测答案生成 gold。
2. **现有 unresolved 的离线诊断。** 零 API；先查已有记录，不为提高支持率而重跑主 Judge。
3. **冻结有限样本 → 第二个真实模型评估 → 一致性检查。** 复用相同证据，不重复搜索。下面给出最多 200 条的建议预算，不是 reviewer 指定的样本数。

**本页没有任何自动 `repeat`、全量抓取、改写标签或自动付费循环。**

## 1. 先定位已有文件，别用新的空目录代替已完成结果

在仓库根目录操作。若有未提交修改，先检查 `git status`，不要用 reset/clean 覆盖本地工作。

```bash
git pull --ff-only origin main
V=reviewer_analysis.revision_v2
P=reviewer_analysis/revision_v2/private

# 只列路径；不要打印或上传 .env、登录记录、API keys。
find "$P" -type f \( -name 'results.jsonl' -o -name 'labels.jsonl' \
  -o -name 'facts.jsonl' -o -name 'pages.jsonl' -o -name 'manifest.json' \
  -o -name 'calibration.json' \) -print
```

按自己的真实路径填写。以下路径是占位说明，**不是宣称本地就叫这些名字**。不要把 125 份首轮结果误当成修复后的 140 份；不要只读取首次失败的记录。

```bash
export FACTS='/你的真实路径/facts.jsonl'
export EXTRACTED='/已验收的140份抽取图/results.jsonl'
export REFERENCE='/原始完整Q4参考图/reference_q4.jsonl'
export PRIMARY_LABELS='/主Judge最终标签/labels.jsonl'
export PRIMARY_ITEMS='/主Judge最终逐项记录/items'
export PRIMARY_MANIFEST='/主Judge对应配置/manifest.json'
export PAGES='/主Judge实际使用的筛查后快照/pages.jsonl'
export ENVFILE='/本地匹配Judge配置.env'
export ALT_ENVFILE='/本地第二模型配置.env'
export REMAIN="$P/remaining_v1"
```

`PRIMARY_ITEMS` 必须与 `PRIMARY_LABELS` 属于同一个最终评估版本。若私有批处理器另有修复账本/目录，先按原有账本定位最终记录，**保留原记录，不能为通过检查直接改标签**。本页的诊断示例会拒绝标签与逐项记录不一致。

## 2. 先完成 Q4 match：不重复 extract

### 输入与停止条件

- 使用原来经作者确认的 Q4 reference；需要完整实体、关系、query ID、版本及适用范围。只做格式转换，不从预测图补造 reference。
- 使用 7 个方法 × 20 题的同一报告抽取视图。不要将某些方法改为 native KG 后与 narrative 抽取混算。
- reference schema、匹配定义和模型配置在匹配前冻结。逐对一对一匹配后由 Python 计数。
- 本流程是新统一 evaluator，不冒充已恢复历史 evaluator。原 evaluator 找回后应核对差异。

```bash
MATCH_OUT="$REMAIN/q4_match_v1"

# dry-run：验证图输入并列任务，不调用模型。
python -m "$V" --env-file "$ENVFILE" match \
  --predictions "$EXTRACTED" --reference "$REFERENCE" \
  --out "$MATCH_OUT" --max-calls 2

# 确认输入齐全，再小批执行。会使用配置的模型服务或CLI额度。
python -m "$V" --env-file "$ENVFILE" match \
  --predictions "$EXTRACTED" --reference "$REFERENCE" \
  --out "$MATCH_OUT" --max-calls 2 --execute

# 检查两份结果的匹配ID、方向与计数。只检查有效性，不按分数调提示词。
# 配置不变时继续剩余项，已成功记录复用。
python -m "$V" --env-file "$ENVFILE" match \
  --predictions "$EXTRACTED" --reference "$REFERENCE" \
  --out "$MATCH_OUT" --max-calls 140 --execute
```

`--max-calls` 是**本次命令的新调用上限**，不是并发数，也不是总任务数。失败文件不会自动重试；存在 `n_failed` 时不能宣布完成。中途停止后可继续尚未开始的任务，但不能自动忽略失败项。更换输入、模型或提示词必须另建版本。

全部有效匹配完成后才计算配对差值。方法名按实际结果中的 `method` 字段填写；以下以 Helicase/ReAct 为例：

```bash
python -m "$V" paired --scores "$MATCH_OUT/results.jsonl" \
  --method-a Helicase --method-b ReAct \
  --expected-queries "$REFERENCE" --out "$REMAIN/paired_Helicase_ReAct.json"
```

对其他预先列出的比较方法同样运行；报告全部比较，不只选择显著者。多重比较的处理应写明。保存逐题分数、匹配对、版本和 reference hash。

**完成标准：**140 个预期 method/run/query 键均有有效结果，无遗漏、重复或未处理错误；20 个原 Q4 query 全覆盖；计数和已定义分数合法。空集合导致的未定义指标须说明。不得 clip 超过 1 的分数，不得删除低分题。query bootstrap 不替代 agent 独立重复，也不解决预算混杂。

## 3. unresolved 离线诊断：零 API

先输出：状态计数、无可用来源、展示片段截断、未展示引用数量、引文校验状态、原始 reason/scope_notes。**这些是处理记录，不是对 921 条事实重新判真伪。**

下面示例只读现有 JSONL/JSON，写入新的私有文件；不会加载密钥或调用网络。要求标准 `items` 记录带 `fact_id` 和 `evidence_payload`。私有驱动格式不同则先保真转换，不伪造缺字段。

```bash
python - <<'PY'
import csv, json, os
from collections import Counter
from pathlib import Path

def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf8').splitlines() if line.strip()]

def indexed(rows, name):
    result = {}
    for row in rows:
        key = row['fact_id']
        if key in result:
            raise ValueError(f'Duplicate fact_id in {name}: {key}')
        result[key] = row
    return result

facts = indexed([f for f in read_rows(os.environ['FACTS'])
                 if f.get('method') == 'Helicase' and f.get('quadrant') == 'Q4'
                 and f.get('fact_type') == 'edge'], 'facts')
all_labels = indexed(read_rows(os.environ['PRIMARY_LABELS']), 'primary labels')
missing = set(facts) - set(all_labels)
if missing:
    raise ValueError(f'{len(missing)} selected facts have no primary label')
labels = {key: all_labels[key] for key in facts}
item_rows = [json.loads(p.read_text(encoding='utf8'))
             for p in sorted(Path(os.environ['PRIMARY_ITEMS']).glob('*.json'))]
items = indexed([r for r in item_rows if r.get('fact_id') in facts], 'primary items')
if set(items) != set(facts):
    raise ValueError('Need the final item record for every selected fact; check repair ledger')
allowed = {'supported', 'contradicted', 'unresolved'}
if any(r.get('truth_status') not in allowed for r in labels.values()):
    raise ValueError('Invalid primary truth_status')
rows = []
for key in sorted(facts):
    label, item = labels[key], items[key]
    if label['truth_status'] != item.get('truth_status'):
        raise ValueError(f'Final labels/items disagree: {key}; reconcile versions, do not overwrite labels')
    if 'evidence_payload' not in item or 'sources' not in item['evidence_payload']:
        raise ValueError(f'Missing original evidence payload: {key}')
    sources = item['evidence_payload']['sources']
    row = {'fact_id': key, 'query_id': facts[key]['query_id'],
           'truth_status': label['truth_status'],
           'validation_status': label.get('validation_status', item.get('validation_status', 'not_recorded')),
           'n_cited_urls': len(facts[key].get('citation_urls', [])),
           'n_sources_shown': len(sources),
           'no_usable_supplied_text': not any(s.get('text') for s in sources),
           'any_shown_source_truncated': any(s.get('truncated') is True for s in sources),
           'n_cited_urls_not_shown': max(0, len(set(facts[key].get('citation_urls', [])))
                                         - len({s.get('url') for s in sources if s.get('url')})),
           'reason': label.get('reason', item.get('reason', '')),
           'scope_notes': label.get('scope_notes', item.get('scope_notes', ''))}
    rows.append(row)
if not rows:
    raise ValueError('No selected facts')
counts = Counter(row['truth_status'] for row in rows)
binary = counts['supported'] + counts['contradicted']
summary = {'n_selected': len(rows), 'status_counts': dict(counts),
           'binary_assessed': binary, 'binary_coverage': binary / len(rows),
           'unresolved_flags': {flag: sum(bool(r[flag]) for r in rows if r['truth_status']=='unresolved')
                for flag in ('no_usable_supplied_text', 'any_shown_source_truncated')},
           'note': 'Flags may overlap. Truncation is observed, not established as the cause of an unresolved label.'}
out = Path(os.environ['REMAIN']) / 'unresolved_diagnostic_v1'
out.mkdir(parents=True, exist_ok=False)
with (out / 'facts.csv').open('w', newline='', encoding='utf8') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
(out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
PY
```

根据已报告结果应见 1,008 条边和 85/2/921。若不同，先核对版本，不强行把计数改成该值。`any_shown_source_truncated` 等标志可重叠，不能相加解释全部 unresolved。

后续只在有具体理由时处理局部项目：已有快照中遗漏相关段落、读取失败或引用身份有误。任何新的证据截取策略必须对预先定义的受影响集合统一应用，保留旧标签并另建版本。不能只修不利结果直到变成 supported。材料仍不足时保留 unresolved。

**完成标准：**每条边可追溯到实际呈现的证据和最终标签；能区分读取/呈现限制与“证据未充分支持”。语义原因（时间、地点、方向、能力与供货混用等）由人员按 reason/原文核对，不能从缺失字段自动推断。

## 4. 第二 Judge：先冻结小样本和同一证据

### 4.1 范围与抽样要求

建议最多 **200 条边**：在当前计数下保留全部 85 supported、2 contradicted，再从 921 unresolved 中抽 113 条。此为**按主 Judge 标签富集的诊断样本**，不是新的 benchmark，也不是总体简单随机样本。

本地执行者应先生成以下文件，再调用第二模型：

- `secondary_sample/facts.jsonl`：原生事实子集，保留原 fact_id、引用顺序和 scope，不改事实。
- `secondary_sample/primary_labels.jsonl`：同一批主 Judge 标签。
- `secondary_sample/selection.json`：源文件 hash、抽样规则、固定抽样随机源、每层总体数/抽中数/包含概率、选中 IDs、主 Judge 配置及证据快照版本。

没有现成的 `sample-secondary` CLI。本段是给本地执行者/编码 agent 的离线准备要求，**不要调用一个不存在的命令**。可用标准库固定随机抽样，先冻结清单，再运行第二模型。不允许看到第二模型标签后更换样本；计数与最新版本不一致时先重新核实设计。缺失主标签和 API 错误须单列，不作为 unresolved 填充。

若需要总体支持率或一致率，必须考虑每层包含概率；否则只报告各层或样本内诊断。仅两个 contradicted 不能支撑稳定的负类性能结论。

### 4.2 使用同一输入，只更换实际模型

第二模型必须确实不同。换 key、assessor 名字，或者再次运行同一个模型，都不是替代 Judge。当前 `codex` 客户端固定主模型配置；不要凭换环境文件就声称它支持任意第二模型。可使用现有 `compatible` 后端和一个已验证可用的不同模型。客户端参数是否被该模型支持，先做小批接口检查；不在这里指定未经账户验证的模型 ID。

保持相同系统提示词、证据页面文件、来源选择顺序、`max_sources`、`chars_per_source`、事实和 scope。若私有主批次的 payload 与公共 `judge` 重建的不一致，先冻结原 evidence_payload 并接入精确重放，不将其当成只改变 Judge 的比较。**quote repair 的处理政策也要一致且留痕。**

```bash
# 这些值必须从 PRIMARY_MANIFEST/原记录填写，不直接假设为默认4/8000。
export PRIMARY_MAX_SOURCES='填原来的数值'
export PRIMARY_CHARS_PER_SOURCE='填原来的数值'
SAMPLE="$REMAIN/secondary_sample"
SECONDARY_OUT="$REMAIN/secondary_judge_v1"

# 先列计划；未准备样本/证据时此步应停止，不自动扩大范围。
python -m "$V" --env-file "$ALT_ENVFILE" judge \
  --facts "$SAMPLE/facts.jsonl" --methods Helicase --quadrants Q4 --fact-type edge \
  --pages "$PAGES" --assessor secondary_judge \
  --max-sources "$PRIMARY_MAX_SOURCES" --chars-per-source "$PRIMARY_CHARS_PER_SOURCE" \
  --out "$SECONDARY_OUT" --max-calls 2

# 确认设置后运行2条。检查模型身份、完整输出以及与主Judge的input_sha256相同。
python -m "$V" --env-file "$ALT_ENVFILE" judge \
  --facts "$SAMPLE/facts.jsonl" --methods Helicase --quadrants Q4 --fact-type edge \
  --pages "$PAGES" --assessor secondary_judge \
  --max-sources "$PRIMARY_MAX_SOURCES" --chars-per-source "$PRIMARY_CHARS_PER_SOURCE" \
  --out "$SECONDARY_OUT" --max-calls 2 --execute

# 同配置继续，其余已完成项复用；最多200个有可用证据的样本调用。
python -m "$V" --env-file "$ALT_ENVFILE" judge \
  --facts "$SAMPLE/facts.jsonl" --methods Helicase --quadrants Q4 --fact-type edge \
  --pages "$PAGES" --assessor secondary_judge \
  --max-sources "$PRIMARY_MAX_SOURCES" --chars-per-source "$PRIMARY_CHARS_PER_SOURCE" \
  --out "$SECONDARY_OUT" --max-calls 200 --execute
```

无可用页面时，当前程序可不调用模型而产生 unresolved。比较中须单列“两边均因无证据而未调用模型”的条目；不能将这类机械一致当作两模型判断高度一致的证据。不能把 `--max-calls 200` 的结束当作样本一定已全部有效完成。

### 4.3 比较与停止标准

```bash
# 仅重新统计这一个冻结样本；不覆盖原全量主Judge calibration目录。
python -m "$V" analyse --facts "$SAMPLE/facts.jsonl" \
  --methods Helicase --quadrants Q4 --fact-type edge \
  --labels "$SAMPLE/primary_labels.jsonl" "$SECONDARY_OUT/labels.jsonl" \
  --out "$REMAIN/secondary_sample_calibration_v1" --bootstrap 2000
```

`analyse` 产生每个 assessor 的条件校准和覆盖率，**不自动产生跨模型一致性表**。本地离线比较还须输出：按 fact_id 对齐的三分类混淆矩阵、各主标签层的一致率、实际调用覆盖率、分歧清单。校准数值之差优先在两模型均可二元判定的**共同事实集合**上另行报告；不能拿不同的已判定子集均值直接归因于模型差异。人工 `agreement` 命令读的是评分 CSV，不接收这些 LLM JSONL。

**完成标准：**模型配置和提示词可追溯；共同事实的 input_sha256 一致；选中ID覆盖完整且错误单列；样本、来源选择和任何修复政策未因结果而改变；报告分歧而非只保留一致部分。不重新搜索，不重新运行 Helicase。模型辅助检查不替代多人专家核验。

## 5. 仍需人类/作者记录，不列入本轮自动API任务

- **人工审核：**复用已生成的400条盲审材料，两人独立填写，先算仲裁前一致性，再保存仲裁版本。空表生成不算完成；案例边的合同/物理流/候选/能力区别与日期范围一起核验。
- **原SCQA说明：**提供原标注人数、资质、日期、参考来源、仲裁、时间/地域范围和测试集使用历史。保留原数据集；不从已看过的问题随机划分出一个“新held-out”。
- **已有消融：**优先找回原 no-UQ/单agent等逐题输出、模型、prompt、停止和预算记录。已有且符合要求的证据直接复用。
- **重复与预算匹配：**Reviewer 1明确提出，仍是未关闭事项。但本页不默认启动80×3或四系统全量任务。只有原记录不足且实验范围确认后，另行执行。当前原生入口只有Full/search_n1；严格四系统后端预算拦截未接通。不要创建同名空开关冒充实验。

这些事项不会因为前三项机器任务结束而自动变成已完成。取舍需在最终response里如实说明，不把有局限的结果写成方法或整个数据集无效。

## 6. 给本地执行者的固定要求与交付物

1. 先盘点已完成结果和版本，禁止全量重复 `extract/pages/primary judge/repeat`。禁止修改核心算法、原 SCQA、gold、主标签和旧统计。
2. 仅在完整原 reference 可用时跑 `match`。无 reference 时输出明确 blocker，继续零API诊断；不得让模型替作者生成 gold。
3. 离线诊断使用最终已验收 items/labels；旧失效项、修复与合并记录继续保留。
4. 第二Judge最多200条作为本次建议预算；先冻结样本及原证据，核对相同输入，再付费。先2条检查，不自动换模型/提示词、不无限重试。
5. 输出到新的 `private/remaining_v1/`，已有目录时检查版本，不能删掉重来。源数据、页面原文、密钥和登录记录不提交GitHub。
6. 生成 `REMAINING_STATUS.md`：逐项 done/blocked/not_started，输入hash，模型与后端，真实处理数/失败数、结果路径、尚待作者确认的事项。报告实际耗时，不承诺未经测量的两天或五天。
7. 最后把结果映射回R1.2（图评分）、R1.3/R2.38（条件校准与覆盖率）、R1.5（替代judge及人工/重复的区别）。旧response中“标签尚不存在”等句子要按新证据更新，但未做的人审、重复和预算匹配不改成完成式。

**这次推送只更新执行说明，没有新增付费运行，也没有把上述离线准备要求冒充已经实现的新CLI。**
