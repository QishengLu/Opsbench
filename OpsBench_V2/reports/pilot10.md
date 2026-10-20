# V2 规则枚举：10-case pilot

全程无 LLM。覆盖率保留全部义务；未通过规则不等于无故障。传播子句只表示请求级关联支持，不是因果证明。

| Case | 候选 | CNF literals | Covered / 全部 | Open |
|---|---:|---:|---:|---:|
| ts2-ts-auth-service-loss-5k6gqr | 10217 | 48 | 3 / 10 | 7 |
| ts2-ts-auth-service-stress-lq54b9 | 23777 | 15 | 3 / 4 | 1 |
| ts4-ts-order-other-service-delay-mpwtgz | 23481 | 228 | 20 / 34 | 14 |
| ts2-ts-order-other-service-container-kill-48rlds | 15439 | 87 | 19 / 30 | 11 |
| ts5-ts-travel-service-partition-9pdvpn | 22697 | 54 | 7 / 14 | 7 |
| ts4-ts-route-plan-service-exception-ztg25x | 37981 | 40 | 7 / 7 | 0 |
| ts6-ts-security-service-response-replace-code-nj74q4 | 48964 | 48 | 10 / 11 | 1 |
| ts4-ts-food-service-request-abort-gzrt8n | 864 | 19 | 7 / 13 | 6 |
| ts4-ts-user-service-bandwidth-gvv8b5 | 15618 | 60 | 6 / 13 | 7 |
| ts2-ts-travel2-service-response-delay-mxrns5 | 30935 | 196 | 13 / 16 | 3 |

## 未覆盖义务

- **ts2-ts-auth-service-loss-5k6gqr**: node:mysql, dependency:mysql->ts-auth-service, propagation:mysql->ts-auth-service, dependency:ts-auth-service->mysql, propagation:ts-auth-service->mysql, propagation:ts-auth-service->ts-ui-dashboard, root_boundary
- **ts2-ts-auth-service-stress-lq54b9**: propagation:ts-auth-service->ts-ui-dashboard
- **ts4-ts-order-other-service-delay-mpwtgz**: node:mysql, dependency:mysql->ts-order-other-service, propagation:mysql->ts-order-other-service, propagation:ts-order-other-service->ts-seat-service, propagation:ts-order-other-service->ts-security-service, propagation:ts-order-other-service->ts-ui-dashboard, propagation:ts-seat-service->ts-travel-plan-service, propagation:ts-seat-service->ts-travel-service, propagation:ts-seat-service->ts-travel2-service, propagation:ts-security-service->ts-preserve-service, propagation:ts-travel-plan-service->ts-ui-dashboard, propagation:ts-travel-service->ts-preserve-service, propagation:ts-travel2-service->ts-ui-dashboard, root_boundary
- **ts2-ts-order-other-service-container-kill-48rlds**: node:ts-travel-service, propagation:ts-order-other-service->ts-seat-service, propagation:ts-order-other-service->ts-security-service, propagation:ts-order-other-service->ts-ui-dashboard, propagation:ts-preserve-service->ts-ui-dashboard, propagation:ts-seat-service->ts-travel-plan-service, propagation:ts-seat-service->ts-travel-service, propagation:ts-security-service->ts-preserve-service, propagation:ts-travel-plan-service->ts-ui-dashboard, propagation:ts-travel-service->ts-preserve-service, propagation:ts-travel2-service->ts-ui-dashboard
- **ts5-ts-travel-service-partition-9pdvpn**: node:ts-travel-plan-service, node:ts-travel-service, propagation:ts-route-plan-service->ts-travel-plan-service, propagation:ts-travel-plan-service->ts-ui-dashboard, propagation:ts-travel-service->ts-preserve-service, propagation:ts-travel-service->ts-route-plan-service, root_boundary
- **ts4-ts-route-plan-service-exception-ztg25x**: 无
- **ts6-ts-security-service-response-replace-code-nj74q4**: propagation:ts-preserve-service->ts-ui-dashboard
- **ts4-ts-food-service-request-abort-gzrt8n**: node:ts-preserve-service, node:ts-train-food-service, propagation:ts-food-service->ts-preserve-service, propagation:ts-preserve-service->ts-ui-dashboard, propagation:ts-train-food-service->ts-food-service, root_boundary
- **ts4-ts-user-service-bandwidth-gvv8b5**: node:mysql, dependency:mysql->ts-user-service, propagation:mysql->ts-user-service, propagation:ts-preserve-service->ts-ui-dashboard, propagation:ts-user-service->ts-preserve-service, propagation:ts-user-service->ts-ui-dashboard, root_boundary
- **ts2-ts-travel2-service-response-delay-mxrns5**: propagation:ts-seat-service->ts-travel2-service, propagation:ts-travel-plan-service->ts-ui-dashboard, propagation:ts-travel2-service->ts-route-plan-service
