# Processing

本目录位于合并仓库根目录下，与 `OpsBench_V2/` 并列。默认使用仓库内的
`OpsBench_V2/data/index/pilot10-portable.jsonl` 和 10 个验证 case；
完整 500-case 数据若另行准备，可用 `--index` 指定其索引。

基于论文和固定公开代码版本，将三种处理方式应用到相同 RCABench 原始数据：

| 方法 | 实现与范围 |
|---|---|
| FoundRoot | normal 窗口估计均值/样本标准差，abnormal 窗口做双向 k-sigma 筛选，保留入选序列完整真实采样值 |
| OpsAgent | 3-sigma + 发布的 CNN 形态分类；Drain3 + 关键词 + TF–IDF；高延迟 span、分钟窗口、三跳路径 |
| V2 | 只读调用现有 OpsBench_V2 枚举器，全部新结果写入本项目 |

这是 **RCABench 数据适配实现**，不是对原论文数据集结果的逐字节复现。
固定来源与具体差异见 `SOURCES.md`，每次运行另存 profile、代码和数据哈希。

## 运行

```bash
cd Processing
python -m venv .venv
.venv/bin/python -m pip install -e '.[shape,test]'
.venv/bin/python -m rca_processing.fetch_assets
.venv/bin/python -m pytest tests -q

# 默认仓库内 pilot10 索引中的第一个 case
.venv/bin/python -m rca_processing --output outputs/pilot-001

# 指定 case，三个方法使用完全相同的 telemetry 与修订 GT
.venv/bin/python -m rca_processing \
  --case ts4-ts-route-plan-service-exception-ztg25x \
  --output outputs/route-001

# 离线同路径范围比较：三个方法都限制到参考路径实体
.venv/bin/python -m rca_processing --scope path \
  --case ts4-ts-route-plan-service-exception-ztg25x --output outputs/route-path-001

# 整套 500-case 构建需单独提供完整数据索引
.venv/bin/python -m rca_processing --index /path/to/RCAbench/index.jsonl \
  --limit 500 --output outputs/full-001
```

默认数据入口为仓库内的 `OpsBench_V2/data/index/pilot10-portable.jsonl`。可指定 `--index`。
默认 `--methods foundroot,opsagent,v2`；没有 CNN 权重时不会静默伪造形态分类。
`--k` 默认 4，来自 FoundRoot 公开脚本中标为 speculative 的参数。
`--trace-quantile` 默认 .98，跟随 OpsAgent 公开代码；论文 v1 为 .95。

## 证据与传播路径

默认 `--scope global` 下 FoundRoot/OpsAgent 检测器只接收 telemetry，
在读取 GT 之前完成提取。
随后离线读取修订版 `ground_truth/gt.json`，将证据关联到节点、
依赖边、传播边以及适用的根因边界义务。GT 方向是影响传播方向，
对应的实际 caller→callee 方向相反。

V2 原实现使用 GT 限定实体，因此默认全局候选与 V2 不是同搜索范围。
`--scope path` 显式将参考节点作为三种方法的离线提取范围：
logs/traces 按服务过滤，metrics 同时匹配 service/source/destination 维度。
这类产物带 `privileged_extraction=true`，不能作为在线模型输入。
对比文件逐方法标注范围，不能混合两种 scope 报优劣。

候选关联只说明实体或精确 span 路径相关，不证明故障传播。
因此 `candidate_ids` 与 CNF 的 `literals` 分开：

- 论文处理器的候选默认未经审核，不自动成为 CNF 真值。
- `--reviews` 接收 `case_id → method → obligation_id → evidence_id → verdict`，
  verdict 为 `supports`、`refutes`、`unresolved`。只有 supports 进入子句。
- 缺少有效证据的义务保留空子句，不删除分母。
- V2 保留已有规则判断，标注为 `registered_rules`，不是专家认证。

可以在审核时补录未被简单关联器自动关联的、已选中的证据，
但不能引用不存在/未入选的 evidence ID。通过新输出目录重建，保留历史结果。

## 输出

```text
outputs/<run>/
  run.json                 # 数据索引、代码、checkpoint 来源、状态
  summary.json
  <case_id>/
    provenance.json        # 原始文件和修订 GT 的 SHA-256
    comparison.json
    foundroot|opsagent|v2/
      candidates.jsonl     # 包括过滤掉的检测候选及原因
      path_evidence.jsonl  # 与参考路径关联或经审核支持的证据集合
      profile.json         # 具体实现、参数、与来源的差异
      phi.json             # 候选关联与审核后的义务
      phi.cnf              # 仅有效 supports，空子句显式保留
      variables.json
      queries.json         # V2 SQL 回放记录
```

FoundRoot 被筛掉的序列仅存统计与精确维度选择器；入选序列存全部值。
OpsAgent 存原始行号和精确 span 引用，以便回溯被压缩文本背后的观测。
候选数量与字符量的粒度不同，不能直接作为方法质量排名。
当前比较报告不伪造 precision/recall；这需要独立证据审核。

这里不训练模型，也不读取或改写 Aiops_RL 的冻结训练划分。
复用 V2 枚举器时，读取同级的 `OpsBench_V2` 项目；不修改其源文件或产物。
