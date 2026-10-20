# OpsBench V2

根据勘误版根因传播图，以确定性规则枚举 telemetry 候选与证据，再生成 CNF。构建和验证不调用 agent / LLM，不读取 `.env`，不使用故障名称、注入参数或标注的异常状态来决定证据是否成立。

## 运行

```bash
python -m pip install -e '.[test]'
# 当前已准备原 pilot10 的数据，通常不需要再次提取：
python -m opsbench_v2.prepare_cases --cases data/index/pilot10.txt
python -m opsbench_v2.pipeline --cases data/index/pilot10.txt
python -m opsbench_v2.verify --cases data/index/pilot10.txt
python -m pytest -q
```

单 case：`python -m opsbench_v2.pipeline --cases <case_id>`。批次汇总文件会对应最后一次运行；每个 case 的产物独立保存。

`prepare_cases.py` 复用了 OpsBench 的提取逻辑，annotations tar 中的 GT 优先于主数据包。`data/raw/follow-the-trace-artifacts` 是本机原始归档的只读用途软链接；生成后的 `data/cases/` 是 V2 自己保存的本地文件。旧项目代码、证据和配置未修改。提取器保留原始注入/SLO 元数据以便溯源，但枚举器只读取 `gt.json` 与 telemetry parquet。

## 产物

- `phi/<case>.yaml`：参考图、完整义务、OR 替代证据、判据、正常/异常观测及 query refs。
- `phi/<case>.cnf` / `.variables.json`：DIMACS CNF 与变量到证据 ID 的映射。
- `evidence/<case>/manifest.json`：源文件/GT/代码哈希、全部 schema、各表时间范围和完整行查询 SQL。
- `evidence/<case>/queries.json`：全部 SQL、完整聚合返回、结果哈希；没有 LIMIT / top-k 裁剪。
- `evidence/<case>/candidates.jsonl`：全部枚举项，包括 `supports`、`not_met`、`insufficient` 和 `context`。
- `reports/pilot10.md` / `summary.json`：批次结果与逐项缺口。
- `reports/cases/<case>.md`：按义务和规则汇总的人工审阅表。
- `reports/verification.json`：逐条 SQL 回放、全候选/完整 CNF 重建一致性结果。

原始 parquet 保留全部服务、全部列、全部观测。manifest 的 `full_row_selector_sql` 可提取路径节点及直接命名这些节点的 metric 维度。边规则还会对 trace 父子链和日志做精确关联。JSON 中保存完整聚合结果；逐行原始 telemetry 从源 parquet 读取，避免将原始日志复制到每条 CNF literal。

## 规则与枚举边界

规则版本见 `opsbench_v2/rules.py`。枚举空间是正常/异常窗口实际出现的分组并集 × 注册规则；不是无限故障机制空间。所有候选跑完才组装，无搜索预算、随机种子、提前停止或 LLM 裁决。

| 范围 | 枚举维度及判据 |
|---|---|
| 节点 traces | 服务、operation + span kind + method、再加 pod；median/p95/p99 延迟增幅、错误率与 4xx 比例；请求量仅保留上下文 |
| 日志 | 全部服务/level/template；缺 template 时按完整 message 枚举；固定正则的连接、超时、DNS、解析、应用异常、一般错误发生比例；启动文本仅为上下文 |
| gauge metrics | 保留所有维度逐序列比较；登记的 CPU 使用量增长、重启计数增长和 ready/available 数量下降可以支持节点；其他数值变化为上下文 |
| sum / histogram | 所有维度、计数、范围及原始值摘要；缺单位、temporality 时不推断 rate、累计量或 histogram quantile |
| 边 dependency | 同 trace 的 CLIENT→SERVER，或网关式 SERVER→SERVER 直接父子关系；失败孤立 CLIENT 需同 trace + span + 调用时间内日志的唯一精确 URL hostname |
| 边异常 | 精确绑定调用的延迟、错误比例、CLIENT/SERVER 方法不一致；根因边界端点使用“involvement”语义 |
| 传播观测 | 沿同服务父链穿过 INTERNAL 找最近 SERVER；错误调用与包含它的上层错误、或显著变慢的调用占上层请求主要耗时；保留完整组合判据 |

默认至少正常/异常各 5 条样本；延迟同时满足 ≥3 倍和 ≥20 ms 增量；错误至少 3 次且错误比例增长 ≥5 个百分点、≥2 倍。日志使用 ≥1 个百分点、≥3 倍。CPU 同时要求均值 ≥3 倍且增量 ≥0.5 原生单位。参数是未经独立校准的 pilot 启发式，不代表统计显著性或误报保证。不同分位数、分组和日志规则可能相关，它们是 OR 替代证据，不是独立投票。

缺正常样本不自动判新增故障；count 减少不自动判服务宕机；未通过规则不代表 refuted；MYSQL 相关 INTERNAL span 不自动解释成数据库执行；无目标绑定的孤立调用不分摊到所有下游；重复 `(trace_id, span_id)` 会使构建失败，避免关联倍增。

## CNF 语义

每个节点以及每条边的 dependency / propagation observation 各有一个义务。若两个根因节点直接相连，额外保留 root boundary 义务，且两个节点明确改为 involvement；边界证据不会偷换成“callee 本地异常”。双向标注仍保留两条有方向的边，不能凭 GT 推断哪一条是可观测调用。

`Φ = ∧ obligation (∨ complete_witness)`。每个 literal 已经是完整规则/组合证据，内部要求的 AND 不会展开成 OR。只有通过规则并确实支持该义务的候选进入子句。原始候选与上下文另存。

没有证据的义务保留空子句，状态 `open`，整例为 `needs_review`。DIMACS 空子句意味着当前严格公式不可满足；这是显式未完成参考证明，不表示真实根因不存在，也不是一个可宣称完全覆盖的 gold case。所有义务保留在覆盖率分母，未自动设置 `observable=false`。

传播规则只建立与标注方向相容的请求级关联/耗时包含关系，**不能从观测性 telemetry 证明因果，也不识别具体注入机制**。所报覆盖率是上述操作化义务的覆盖率。

## 可复现性与评测边界

ID 由规则和实体/分组稳定哈希生成，SQL 有确定排序、固定 UTC、单线程聚合，所有原始文件和引擎文件有 SHA-256。验证器检查输入哈希，逐条重跑 SQL，重新生成整个候选空间和 CNF 并比较，而不是只检查 YAML 格式。另有合成数据测试约束归属和空子句等语义。回放一致性不是专家对所有证据有效性的认证。

这些文件使用 GT 确定检索范围，是离线参考构建产物。在线评测不能把 reference_path、规则生成的正确路径证据或缺失义务清单直接给待测 agent；仍应给全局 telemetry 和正常告警输入。pilot10 沿用 V1 的样本便于比较，不是新划分的 held-out 集，不报告泛化性能。

当前未覆盖：无可确认目标的 DB/网络访问、跨服务非父子且无精确绑定的传播、日志深层语义、未知 metric 单位/temporality、没有可靠请求机会的可用性证明。扩展应增加通用规则与反例测试，不能按单个 case 降阈值以补齐覆盖率。
