# ts4-ts-food-service-request-abort-gzrt8n

状态：needs_review；7/13 条义务有规则证据。

这些是离线参考标注。传播支持表示请求级关联，不证明因果。所有未覆盖义务保留。

| 义务 | 含义 | 状态 | 规则及证据数 |
|---|---|---|---|
| node:ts-food-service | node_involvement | covered | trace_rate_errors: 7 |
| node:ts-preserve-service | node_anomaly | open | 证据不足 |
| node:ts-train-food-service | node_involvement | open | 证据不足 |
| node:ts-ui-dashboard | node_anomaly | covered | trace_latency_p95_ms: 2, trace_latency_p99_ms: 2, trace_rate_errors: 3 |
| dependency:ts-food-service->ts-preserve-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-food-service->ts-preserve-service | propagation_observation | open | 证据不足 |
| dependency:ts-food-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 1 |
| propagation:ts-food-service->ts-ui-dashboard | propagation_observation | covered | server_parent_linked_errors: 1 |
| dependency:ts-preserve-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 1 |
| propagation:ts-preserve-service->ts-ui-dashboard | propagation_observation | open | 证据不足 |
| dependency:ts-train-food-service->ts-food-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-train-food-service->ts-food-service | propagation_observation | open | 证据不足 |
| root_boundary | boundary_anomaly | open | 证据不足 |

原始数据、完整 SQL 及全部候选在 `data/cases/` 和 `evidence/` 中；本表按规则归并展示，CNF 中不裁剪替代证据。
