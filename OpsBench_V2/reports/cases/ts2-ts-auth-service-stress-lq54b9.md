# ts2-ts-auth-service-stress-lq54b9

状态：needs_review；3/4 条义务有规则证据。

这些是离线参考标注。传播支持表示请求级关联，不证明因果。所有未覆盖义务保留。

| 义务 | 含义 | 状态 | 规则及证据数 |
|---|---|---|---|
| node:ts-auth-service | node_anomaly | covered | metric_series_summary: 2 |
| node:ts-ui-dashboard | node_anomaly | covered | trace_latency_p95_ms: 2, trace_latency_p99_ms: 10 |
| dependency:ts-auth-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 1 |
| propagation:ts-auth-service->ts-ui-dashboard | propagation_observation | open | 证据不足 |

原始数据、完整 SQL 及全部候选在 `data/cases/` 和 `evidence/` 中；本表按规则归并展示，CNF 中不裁剪替代证据。
