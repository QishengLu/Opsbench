# ts2-ts-travel2-service-response-delay-mxrns5

状态：needs_review；13/16 条义务有规则证据。

这些是离线参考标注。传播支持表示请求级关联，不证明因果。所有未覆盖义务保留。

| 义务 | 含义 | 状态 | 规则及证据数 |
|---|---|---|---|
| node:ts-route-plan-service | node_anomaly | covered | trace_latency_median_ms: 12, trace_latency_p95_ms: 15, trace_latency_p99_ms: 17 |
| node:ts-seat-service | node_involvement | covered | edge_latency_median_ms: 1, edge_latency_p95_ms: 1, edge_latency_wait_ms: 1, trace_latency_p95_ms: 6, trace_latency_p99_ms: 4 |
| node:ts-travel-plan-service | node_anomaly | covered | trace_latency_median_ms: 12, trace_latency_p95_ms: 15, trace_latency_p99_ms: 15 |
| node:ts-travel2-service | node_involvement | covered | edge_latency_median_ms: 1, edge_latency_p95_ms: 1, edge_latency_wait_ms: 1, trace_latency_median_ms: 10, trace_latency_p95_ms: 11, trace_latency_p99_ms: 11, trace_rate_errors: 4 |
| node:ts-ui-dashboard | node_anomaly | covered | trace_latency_median_ms: 8, trace_latency_p95_ms: 16, trace_latency_p99_ms: 21 |
| dependency:ts-route-plan-service->ts-travel-plan-service | dependency | covered | matched_dependency: 3 |
| propagation:ts-route-plan-service->ts-travel-plan-service | propagation_observation | covered | edge_nested_latency: 3 |
| dependency:ts-seat-service->ts-travel2-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-seat-service->ts-travel2-service | propagation_observation | open | 证据不足 |
| dependency:ts-travel-plan-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 3 |
| propagation:ts-travel-plan-service->ts-ui-dashboard | propagation_observation | open | 证据不足 |
| dependency:ts-travel2-service->ts-route-plan-service | dependency | covered | matched_dependency: 4 |
| propagation:ts-travel2-service->ts-route-plan-service | propagation_observation | open | 证据不足 |
| dependency:ts-travel2-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 1 |
| propagation:ts-travel2-service->ts-ui-dashboard | propagation_observation | covered | server_parent_nested_latency: 1 |
| root_boundary | boundary_anomaly | covered | edge_latency_median_ms: 1, edge_latency_p95_ms: 1, edge_latency_wait_ms: 1 |

原始数据、完整 SQL 及全部候选在 `data/cases/` 和 `evidence/` 中；本表按规则归并展示，CNF 中不裁剪替代证据。
