# ts4-ts-user-service-bandwidth-gvv8b5

状态：needs_review；6/13 条义务有规则证据。

这些是离线参考标注。传播支持表示请求级关联，不证明因果。所有未覆盖义务保留。

| 义务 | 含义 | 状态 | 规则及证据数 |
|---|---|---|---|
| node:mysql | node_involvement | open | 证据不足 |
| node:ts-preserve-service | node_anomaly | covered | trace_latency_p95_ms: 1 |
| node:ts-ui-dashboard | node_anomaly | covered | trace_latency_median_ms: 3, trace_latency_p95_ms: 3, trace_latency_p99_ms: 3 |
| node:ts-user-service | node_involvement | covered | log_connection_failure: 1, log_error_message: 1, log_timeout: 1, trace_latency_median_ms: 11, trace_latency_p95_ms: 11, trace_latency_p99_ms: 11, trace_rate_errors: 11 |
| dependency:mysql->ts-user-service | dependency | open | 证据不足 |
| propagation:mysql->ts-user-service | propagation_observation | open | 证据不足 |
| dependency:ts-preserve-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 1 |
| propagation:ts-preserve-service->ts-ui-dashboard | propagation_observation | open | 证据不足 |
| dependency:ts-user-service->ts-preserve-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-user-service->ts-preserve-service | propagation_observation | open | 证据不足 |
| dependency:ts-user-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 1 |
| propagation:ts-user-service->ts-ui-dashboard | propagation_observation | open | 证据不足 |
| root_boundary | boundary_anomaly | open | 证据不足 |

原始数据、完整 SQL 及全部候选在 `data/cases/` 和 `evidence/` 中；本表按规则归并展示，CNF 中不裁剪替代证据。
