# Handoff — 2026-10-20

## 当前目标与状态

仓库将 `Processing` 和 `OpsBench_V2` 放在同一根目录。统一入口运行
FoundRoot、OpsAgent、V2 三种方法；V2 pilot10 的 case 输入、候选证据、
CNF 和验证报告均在仓库内。`Processing` 是 RCABench 数据适配，
不是对 FoundRoot/OpsAgent 原论文报告指标的直接复现。

## 从哪里开始

1. 先读根目录 `README.md`、`Processing/README.md`、`Processing/SOURCES.md`、
   `Processing/VALIDATION.md`、`OpsBench_V2/README.md`。
2. Python 3.11+；按根目录 README 建虚拟环境并安装两个包。
3. 运行两套测试。以 `Processing` 的统一入口跑一个 pilot case，使用新的
   `--output` 目录；旧输出路径存在时命令会拒绝覆盖。
4. 若需检查 V2 已保存的 pilot10，运行
   `(cd OpsBench_V2 && ../.venv/bin/python -m opsbench_v2.verify --cases data/index/pilot10.txt)`。
   此命令会回放 SQL 并覆盖 `reports/verification.json`，先确认是否要保留原文件。

## 关键位置与数据契约

- `Processing/rca_processing/__main__.py`：统一 CLI、三方法运行、产物组织。
- `Processing/rca_processing/common.py`：默认索引及 telemetry 读取。
- `Processing/rca_processing/v2.py`：只读调用同级 V2 枚举器。
- `OpsBench_V2/opsbench_v2/enumerate.py`、`rules.py`、`verify.py`：V2 枚举、规则、回放。
- `OpsBench_V2/data/index/pilot10-portable.jsonl`：可移植的 10-case 索引。
- `OpsBench_V2/data/cases/<case>/`：telemetry parquet、GT、注入和 SLO 元数据。
- `OpsBench_V2/evidence/<case>/`：全部候选和 SQL，文件较大；不能仅凭
  `reports/verification.json` 声称专家验证。
- `OpsBench_V2/phi/<case>.*`：义务、CNF、变量映射。

`Processing` 的 FoundRoot/OpsAgent 默认先从全局 telemetry 抽取证据，再按
GT 做离线关联；V2 原实现按 GT 范围枚举。公平比较搜索范围时用 `--scope path`，
但这属于特权离线提取，不能作为在线 agent 输入。`candidate_ids` 只表示关联；
人工审核为 `supports` 的证据才进入前两种方法的 CNF literal。
V2 的 `supports` 是注册规则判定，不等于独立专家认证。空子句保留未覆盖义务。

## 已知限制与建议的后续工作

1. `Processing/VALIDATION.md` 仅记录 3 个真实 case 的冒烟运行；未跑完整
   500-case，也未有独立证据审核或模型准确率评测。
2. 完整 500-case 数据在原开发机的同级 `datasets/RCAbench`，未上传。
   若需要跑全量数据，提供独立索引并用 `--index` 指定；不要把本地绝对路径写入仓库。
3. OpsAgent CNN 权重的来源和 SHA-256 在 `Processing/assets/patterncla.source.json`；
   如需换权重，先核对来源和许可证，保留哈希溯源。
4. 优先建立独立人工证据审核，再评估三方法的覆盖与代价；不要用候选条数
   或 V2 规则覆盖率直接排序方法质量。
5. 扩展 V2 规则时，增加通用规则与反例测试，避免针对单个 case 调阈值。
