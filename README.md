# Opsbench

同一份 RCABench case 上的三种证据处理方法：FoundRoot、OpsAgent 和 OpsBench V2。
`Processing/` 提供统一运行及比较入口；`OpsBench_V2/` 提供 V2 的确定性枚举器、
10 个验证 case 的原始 telemetry、CNF、证据与回放报告。

## 目录

| 路径 | 用途 |
|---|---|
| `Processing/` | 三种方法的统一适配、比较、测试及来源说明 |
| `OpsBench_V2/data/cases/` | pilot10 的 telemetry、修订 GT 和来源元数据 |
| `OpsBench_V2/evidence/` | V2 的 manifest、SQL、候选证据 |
| `OpsBench_V2/phi/` | V2 的 YAML、DIMACS CNF、变量映射 |
| `OpsBench_V2/reports/` | pilot10 汇总、逐 case 审阅表和验证结果 |

## 快速验证

需要 Python 3.11+。在仓库根目录执行：

```bash
python -m venv .venv
.venv/bin/python -m pip install -e './Processing[shape,test]' -e './OpsBench_V2[test]'
(cd Processing && ../.venv/bin/python -m pytest -q)
(cd OpsBench_V2 && ../.venv/bin/python -m pytest -q)
cd Processing
../.venv/bin/python -m rca_processing --case ts4-ts-route-plan-service-exception-ztg25x --output outputs/route-smoke
```

默认索引 `OpsBench_V2/data/index/pilot10-portable.jsonl` 使用相对路径，克隆后可直接运行。
完整 500-case 数据未随仓库上传；其索引可通过 `--index` 指定。V2 回放验证命令见
[`OpsBench_V2/README.md`](OpsBench_V2/README.md)，来源及方法边界见
[`Processing/SOURCES.md`](Processing/SOURCES.md)。后续任务见 [`handoff.md`](handoff.md)。
