# ts6-ts-security-service-response-replace-code-nj74q4

状态：needs_review；10/11 条义务有规则证据。

这些是离线参考标注。传播支持表示请求级关联，不证明因果。所有未覆盖义务保留。

| 义务 | 含义 | 状态 | 规则及证据数 |
|---|---|---|---|
| node:ts-order-service | node_involvement | covered | edge_error_rate: 1, trace_latency_p99_ms: 6 |
| node:ts-preserve-service | node_anomaly | covered | log_error_message: 1, trace_rate_errors: 7 |
| node:ts-security-service | node_involvement | covered | edge_error_rate: 1, log_error_message: 1, trace_latency_p99_ms: 3, trace_rate_errors: 7 |
| node:ts-ui-dashboard | node_anomaly | covered | log_error_message: 1, trace_latency_p95_ms: 6, trace_latency_p99_ms: 8, trace_rate_errors: 2 |
| dependency:ts-order-service->ts-security-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-order-service->ts-security-service | propagation_observation | covered | edge_linked_error_increase: 1 |
| dependency:ts-preserve-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 1 |
| propagation:ts-preserve-service->ts-ui-dashboard | propagation_observation | open | 证据不足 |
| dependency:ts-security-service->ts-preserve-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-security-service->ts-preserve-service | propagation_observation | covered | edge_linked_error_increase: 1 |
| root_boundary | boundary_anomaly | covered | edge_error_rate: 1 |

原始数据、完整 SQL 及全部候选在 `data/cases/` 和 `evidence/` 中；本表按规则归并展示，CNF 中不裁剪替代证据。
