# ts4-ts-route-plan-service-exception-ztg25x

状态：complete；7/7 条义务有规则证据。

这些是离线参考标注。传播支持表示请求级关联，不证明因果。所有未覆盖义务保留。

| 义务 | 含义 | 状态 | 规则及证据数 |
|---|---|---|---|
| node:ts-route-plan-service | node_anomaly | covered | log_error_message: 1, trace_rate_errors: 5 |
| node:ts-travel-plan-service | node_anomaly | covered | log_error_message: 1, trace_rate_errors: 7 |
| node:ts-ui-dashboard | node_anomaly | covered | trace_latency_p95_ms: 2, trace_latency_p99_ms: 14, trace_rate_errors: 2 |
| dependency:ts-route-plan-service->ts-travel-plan-service | dependency | covered | matched_dependency: 3 |
| propagation:ts-route-plan-service->ts-travel-plan-service | propagation_observation | covered | edge_linked_error_increase: 1 |
| dependency:ts-travel-plan-service->ts-ui-dashboard | dependency | covered | server_parent_dependency: 3 |
| propagation:ts-travel-plan-service->ts-ui-dashboard | propagation_observation | covered | server_parent_linked_errors: 1 |

原始数据、完整 SQL 及全部候选在 `data/cases/` 和 `evidence/` 中；本表按规则归并展示，CNF 中不裁剪替代证据。
