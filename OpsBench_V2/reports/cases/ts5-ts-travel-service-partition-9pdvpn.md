# ts5-ts-travel-service-partition-9pdvpn

状态：needs_review；7/14 条义务有规则证据。

这些是离线参考标注。传播支持表示请求级关联，不证明因果。所有未覆盖义务保留。

| 义务 | 含义 | 状态 | 规则及证据数 |
|---|---|---|---|
| node:ts-preserve-service | node_involvement | covered | log_connection_failure: 1, log_error_message: 1, log_timeout: 1, trace_latency_median_ms: 6, trace_latency_p95_ms: 7, trace_latency_p99_ms: 7, trace_rate_errors: 7 |
| node:ts-route-plan-service | node_anomaly | covered | trace_latency_p95_ms: 4 |
| node:ts-travel-plan-service | node_anomaly | open | 证据不足 |
| node:ts-travel-service | node_involvement | open | 证据不足 |
| node:ts-ui-dashboard | node_anomaly | covered | trace_latency_median_ms: 2, trace_latency_p95_ms: 2, trace_latency_p99_ms: 5 |
| dependency:ts-route-plan-service->ts-travel-plan-service | dependency | covered | matched_dependency: 3 |
| propagation:ts-route-plan-service->ts-travel-plan-service | propagation_observation | open | 证据不足 |
| dependency:ts-travel-plan-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 3 |
| propagation:ts-travel-plan-service->ts-ui-dashboard | propagation_observation | open | 证据不足 |
| dependency:ts-travel-service->ts-preserve-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-travel-service->ts-preserve-service | propagation_observation | open | 证据不足 |
| dependency:ts-travel-service->ts-route-plan-service | dependency | covered | matched_dependency: 4 |
| propagation:ts-travel-service->ts-route-plan-service | propagation_observation | open | 证据不足 |
| root_boundary | boundary_anomaly | open | 证据不足 |

原始数据、完整 SQL 及全部候选在 `data/cases/` 和 `evidence/` 中；本表按规则归并展示，CNF 中不裁剪替代证据。
