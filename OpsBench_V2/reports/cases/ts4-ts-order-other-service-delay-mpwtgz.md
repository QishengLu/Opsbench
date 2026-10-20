# ts4-ts-order-other-service-delay-mpwtgz

状态：needs_review；20/34 条义务有规则证据。

这些是离线参考标注。传播支持表示请求级关联，不证明因果。所有未覆盖义务保留。

| 义务 | 含义 | 状态 | 规则及证据数 |
|---|---|---|---|
| node:mysql | node_involvement | open | 证据不足 |
| node:ts-order-other-service | node_involvement | covered | trace_latency_median_ms: 21, trace_latency_p95_ms: 21, trace_latency_p99_ms: 21 |
| node:ts-preserve-service | node_anomaly | covered | trace_latency_median_ms: 4, trace_latency_p95_ms: 2, trace_latency_p99_ms: 2 |
| node:ts-seat-service | node_anomaly | covered | trace_latency_p95_ms: 11, trace_latency_p99_ms: 7 |
| node:ts-security-service | node_anomaly | covered | trace_latency_median_ms: 6, trace_latency_p95_ms: 7, trace_latency_p99_ms: 7 |
| node:ts-travel-plan-service | node_anomaly | covered | trace_latency_median_ms: 8, trace_latency_p95_ms: 11, trace_latency_p99_ms: 11 |
| node:ts-travel-service | node_anomaly | covered | trace_latency_p95_ms: 12, trace_latency_p99_ms: 1 |
| node:ts-travel2-service | node_anomaly | covered | trace_latency_median_ms: 10, trace_latency_p95_ms: 11, trace_latency_p99_ms: 11 |
| node:ts-ui-dashboard | node_anomaly | covered | trace_latency_median_ms: 10, trace_latency_p95_ms: 9, trace_latency_p99_ms: 11 |
| dependency:mysql->ts-order-other-service | dependency | open | 证据不足 |
| propagation:mysql->ts-order-other-service | propagation_observation | open | 证据不足 |
| dependency:ts-order-other-service->ts-seat-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-order-other-service->ts-seat-service | propagation_observation | open | 证据不足 |
| dependency:ts-order-other-service->ts-security-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-order-other-service->ts-security-service | propagation_observation | open | 证据不足 |
| dependency:ts-order-other-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 1 |
| propagation:ts-order-other-service->ts-ui-dashboard | propagation_observation | open | 证据不足 |
| dependency:ts-preserve-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 1 |
| propagation:ts-preserve-service->ts-ui-dashboard | propagation_observation | covered | server_parent_nested_latency: 1 |
| dependency:ts-seat-service->ts-travel-plan-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-seat-service->ts-travel-plan-service | propagation_observation | open | 证据不足 |
| dependency:ts-seat-service->ts-travel-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-seat-service->ts-travel-service | propagation_observation | open | 证据不足 |
| dependency:ts-seat-service->ts-travel2-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-seat-service->ts-travel2-service | propagation_observation | open | 证据不足 |
| dependency:ts-security-service->ts-preserve-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-security-service->ts-preserve-service | propagation_observation | open | 证据不足 |
| dependency:ts-travel-plan-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 3 |
| propagation:ts-travel-plan-service->ts-ui-dashboard | propagation_observation | open | 证据不足 |
| dependency:ts-travel-service->ts-preserve-service | dependency | covered | matched_dependency: 1 |
| propagation:ts-travel-service->ts-preserve-service | propagation_observation | open | 证据不足 |
| dependency:ts-travel2-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 1 |
| propagation:ts-travel2-service->ts-ui-dashboard | propagation_observation | open | 证据不足 |
| root_boundary | boundary_anomaly | open | 证据不足 |

原始数据、完整 SQL 及全部候选在 `data/cases/` 和 `evidence/` 中；本表按规则归并展示，CNF 中不裁剪替代证据。
