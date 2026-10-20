# Validation — 2026-10-20

All three processors ran on real telemetry from the shared 500-case dataset.
Three cases were exercised; no 500-case processing campaign or model accuracy
benchmark is claimed.

| Case | FoundRoot selected metric series | OpsAgent selected candidates | V2 CNF witnesses |
|---|---:|---:|---:|
| ts4-ts-route-plan-service-exception-ztg25x | 1043 | 136 | 40 |
| ts2-ts-auth-service-stress-lq54b9 | 658 | 134 | 15 |
| ts0-mysql-container-kill-9t6n24 | 508 | 108 | 20 |

Saved runs: `outputs/pilot_route_v1`, `outputs/pilot_auth_stress_v1`,
`outputs/final_smoke_001`. The last includes the explicit `path_evidence.jsonl`
export added after the first two runs. Each run records source hashes.

These counts have different granularities: full metric series, anomaly events/
templates/windows, and complete rule witnesses. They must not be ranked directly.
No external manual reviews were supplied, so FoundRoot/OpsAgent's reviewed CNF
coverage is zero, while candidate associations are recorded separately.
V2's registered-rule coverage is not independent expert validation.

For the route-plan and auth-stress cases, every V2 obligation's literal list
exactly matches the existing `OpsBench_V2/phi` artifact after rerunning on the
centralized dataset. The adapter did not change the old rule implementation.

Seven tests passed: k-sigma/zero variance, path association vs reviewed support,
real CNN checkpoint loading/inference, cross-trace span identity, log
template/keyword filtering, missing modalities, and path-scope filtering with
original row identities preserved.

An additional matched-path-scope run completed at `outputs/path_scope_smoke_001`
on the route-plan case: FoundRoot retained 37 series, OpsAgent retained 51
candidates, V2 retained 40 witnesses. Candidate-associated obligations were
3/7, 7/7 and 7/7 respectively. The first two remain unreviewed. This run avoids
the default comparison's scope difference (global detectors versus GT-scoped V2),
but does not remove differences in evidence granularity or establish accuracy.

The independently downloaded CNN checkpoint passed its pinned SHA-256 check.
Tests and processing used `Processing/.venv`, separate from Aiops_RL environments.
