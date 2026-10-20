"""Enumerate the complete finite rule/group space. No search budget, LLM or top-k."""
from __future__ import annotations

import json
from pathlib import Path

from .rules import CONTRACT, LOG_PATTERNS, VERSION, increased_latency, increased_rate, metric_shift
from .storage import Store, canonical, digest, file_hash, ident, quote


def err(alias=""):
    p = alias + "." if alias else ""
    return f"coalesce(({p}\"attr.status_code\" IN ('Error','STATUS_CODE_ERROR') OR {p}\"attr.http.response.status_code\" >= 500),false)"


def kind(alias, value):
    return f"lower({alias}.\"attr.span_kind\") IN ('{value}', 'span_kind_{value}')"


def service(component):
    if not component.startswith("service|"):
        raise ValueError(f"Expected service annotation, got {component}")
    return component.split("|", 1)[1]


def make_obligations(gt):
    nodes = sorted({service(n["component"]) for n in gt["nodes"]})
    edges = sorted({(service(e["source"]), service(e["target"])) for e in gt["edges"]})
    roots = sorted({service(r["component"]) for r in gt["root_causes"]})
    if not set(roots).issubset(nodes) or any(a not in nodes or b not in nodes for a, b in edges):
        raise ValueError("GT roots/edges must belong to nodes")
    # Only a directly connected two-root boundary changes node semantics.
    boundary = set(roots) if len(roots) == 2 and any(set(e) == set(roots) for e in edges) else set()
    obs = []
    for n in nodes:
        obs.append({"id": f"node:{n}", "kind": "node_involvement" if n in boundary else "node_anomaly",
                    "subject": {"service": n}, "meaning": "local anomaly OR incident call on annotated root boundary" if n in boundary else "local anomalous telemetry"})
    for src, dst in edges:
        subject = {"source": src, "target": dst, "caller": dst, "callee": src}
        obs.extend([
            {"id": f"dependency:{src}->{dst}", "kind": "dependency", "subject": subject,
             "meaning": "observed caller-to-callee dependency; reverse of annotated impact direction"},
            {"id": f"propagation:{src}->{dst}", "kind": "propagation_observation", "subject": subject,
             "meaning": "request-linked anomalous call and caller symptom compatible with propagation; not causal identification"},
        ])
    if boundary:
        obs.append({"id": "root_boundary", "kind": "boundary_anomaly", "subject": {"ends": roots},
                    "meaning": "anomalous call on this boundary; does not identify injection mechanism or side"})
    return nodes, edges, boundary, obs


class Enumerator:
    def __init__(self, case_dir):
        self.case_dir = Path(case_dir)
        self.gt = json.loads((self.case_dir / "ground_truth/gt.json").read_text())
        self.nodes, self.edges, self.boundary, self.obligations = make_obligations(self.gt)
        self.store = Store(self.case_dir)
        self.candidates, self.inventory = [], {}
        self.node_filter = ",".join(map(quote, self.nodes)) or "NULL"

    def record(self, rule, subject, normal, abnormal, refs, verdict, obligations=(), note="", units=None):
        candidate = {"rule_id": rule, "rule_version": VERSION, "subject": subject,
                     "baseline": normal, "incident": abnormal, "query_refs": sorted(set(refs)),
                     "verdict": verdict, "obligation_ids": sorted(set(obligations)),
                     "note": note, "units": units}
        candidate["id"] = "e_" + digest({"rule": rule, "subject": subject})[:24]
        self.candidates.append(candidate)

    def paired(self, build_sql, purpose, keys):
        windows, refs = {}, []
        for w in ("normal", "abnormal"):
            sql = build_sql(w)
            if sql is None:
                windows[w] = {}
                continue
            qid, rows = self.store.query(sql, purpose)
            refs.append(qid)
            windows[w] = {canonical([r[k] for k in keys]): r for r in rows}
            if len(windows[w]) != len(rows):
                raise ValueError(f"Non-unique grouping for {purpose}")
        for k in sorted(set(windows["normal"]) | set(windows["abnormal"])):
            b, a = windows["normal"].get(k), windows["abnormal"].get(k)
            yield {key: (a or b)[key] for key in keys}, b, a, refs

    def inventory_tables(self):
        for t in self.store.sources:
            if not self.store.has(t):
                self.inventory[t] = {"status": "modality_unavailable"}
                continue
            qid, rows = self.store.query(f"SELECT count(*) n,min(time) first_time,max(time) last_time,"
                f"epoch(max(time)-min(time)) observed_extent_seconds FROM {t}", "table coverage")
            if t.endswith("_traces"):
                iq, duplicates = self.store.query(f"SELECT trace_id,span_id,count(*) n FROM {t} GROUP BY 1,2 HAVING count(*)>1 ORDER BY 1,2", "span identity integrity")
                if duplicates:
                    raise ValueError(f"{t}: nonunique (trace_id,span_id); refusing ambiguous parent joins")
            # Full original rows/columns are retained in local source parquet, not truncated examples.
            schema = self.store.sources[t]["schema"]
            filters = [f"service_name IN ({self.node_filter})"]
            for col in ("attr.source", "attr.destination", "attr.source_workload", "attr.destination_workload", "attr.k8s.service.name"):
                if col in schema:
                    filters.append(f"{ident(col)} IN ({self.node_filter})")
            where = " OR ".join(filters)
            selector = f"SELECT * FROM {t} WHERE {where}"
            cq, counts = self.store.query(f"SELECT count(*) n FROM {t} WHERE {where}", "complete scope count")
            self.inventory[t] = {**rows[0], "status": "available", "query_ref": qid,
                                 "scope_rows": counts[0]["n"], "scope_count_query_ref": cq,
                                 "full_row_selector_sql": selector,
                                 "window_contract": "entire supplied normal/abnormal file; observed extent is NOT exposure"}

    def traces(self):
        for level, keys in [("service", ["service_name"]), ("operation", ["service_name", "span_name", "span_kind", "http_method"]),
                            ("pod_operation", ["service_name", "span_name", "span_kind", "http_method", "pod"])]:
            dims = {"service_name": "service_name", "span_name": "span_name", "span_kind": '"attr.span_kind"',
                    "http_method": '"attr.http.request.method"', "pod": '"attr.k8s.pod.name"'}
            select = ",".join(f"{dims[k]} AS {k}" for k in keys)
            group = ",".join(str(i+1) for i in range(len(keys)))
            def sql(w):
                t = f"{w}_traces"
                if not self.store.has(t):
                    return None
                return f'''SELECT {select},count(*) n,median(duration)/1e6 median_ms,
                  quantile_cont(duration,.95)/1e6 p95_ms,quantile_cont(duration,.99)/1e6 p99_ms,
                  count(*) FILTER (WHERE {err()}) errors,
                  count(*) FILTER (WHERE "attr.http.response.status_code" BETWEEN 400 AND 499) http4xx,
                  min(time) first_time,max(time) last_time FROM {t}
                  WHERE service_name IN ({self.node_filter}) GROUP BY {group} ORDER BY {group}'''
            for subject, b, a, refs in self.paired(sql, f"trace {level}", keys):
                subject = {"scope": level, **subject}
                obligations = [f"node:{subject['service_name']}"]
                for field in ("median_ms", "p95_ms", "p99_ms"):
                    self.record("trace_latency_"+field, subject, b, a, refs, increased_latency(b,a,field), obligations,
                                "Duration belongs to the recorded span kind/operation, not automatically database execution.", "ms")
                for field in ("errors", "http4xx"):
                    self.record("trace_rate_"+field, subject, b,a,refs,increased_rate(b,a,field),obligations,"Fraction of spans, not request availability.","fraction")
                self.record("trace_volume_change",subject,b,a,refs,"context",(),
                            "Counts only: no verified exposure/load opportunity; never infer outage from count decline.","spans")

    def logs(self):
        # Every observed template/level is inventoried, including normal and non-error templates.
        keys = ["service_name", "level", "template"]
        def templates(w):
            t = f"{w}_logs"
            if not self.store.has(t): return None
            template = 'coalesce("attr.log_template",message)' if "attr.log_template" in self.store.sources[t]["schema"] else "message"
            return f'''SELECT service_name,level,{template} AS "template",
                count(*) n,min(time) first_time,max(time) last_time FROM {t}
                WHERE service_name IN ({self.node_filter}) GROUP BY 1,2,3 ORDER BY 1,2,3'''
        for subject,b,a,refs in self.paired(templates,"all log templates",keys):
            self.record("log_template_inventory",subject,b,a,refs,"context",(),"Full messages retained in source parquet; template identity is not itself anomaly proof.")
        for name, pattern in sorted(LOG_PATTERNS.items()):
            def sql(w):
                t = f"{w}_logs"
                if not self.store.has(t): return None
                return f'''SELECT service_name,count(*) n,
                  count(*) FILTER (WHERE regexp_matches(message,{quote(pattern)})) events,
                  min(time) FILTER (WHERE regexp_matches(message,{quote(pattern)})) first_event,
                  max(time) FILTER (WHERE regexp_matches(message,{quote(pattern)})) last_event
                  FROM {t} WHERE service_name IN ({self.node_filter}) GROUP BY 1 ORDER BY 1'''
            for subject,b,a,refs in self.paired(sql,"log pattern "+name,["service_name"]):
                state = increased_rate(b,a,"events",log=True)
                obs = [f"node:{subject['service_name']}"]
                if name == "startup_message":
                    # Startup logs alone do not prove an abnormal restart.
                    state, obs = "context", []
                self.record("log_"+name,subject,b,a,refs,state,obs,
                            "Fixed regex match frequency among this service's logs; overlapping patterns are alternatives, not independent votes.","fraction")

    def metrics(self):
        for modality in ("metrics", "metrics_sum", "metrics_histogram"):
            tables = [f"{w}_{modality}" for w in ("normal", "abnormal")]
            available = [t for t in tables if self.store.has(t)]
            if not available: continue
            schemas = [self.store.sources[t]["schema"] for t in available]
            dims = sorted(set.intersection(*(set(s) for s in schemas)) - {"time", "value", "count", "sum", "min", "max"})
            # Never mix pods, destinations or histogram populations in one metric series.
            select = ",".join(map(ident,dims))
            group = ",".join(str(i+1) for i in range(len(dims)))
            def sql(w):
                t = f"{w}_{modality}"
                if not self.store.has(t): return None
                where = [f"service_name IN ({self.node_filter})"]
                for col in ("attr.source", "attr.destination", "attr.source_workload", "attr.destination_workload", "attr.k8s.service.name"):
                    if col in dims: where.append(f"{ident(col)} IN ({self.node_filter})")
                stats = 'avg(value) mean,min(value) minimum,max(value) maximum' if modality != "metrics_histogram" else 'min("count") minimum_count,max("count") maximum_count,min("min") minimum,max("max") maximum,avg("sum"/nullif("count",0)) mean'
                return f'''SELECT {select},count(*) n,{stats},min(time) first_time,max(time) last_time
                  FROM {t} WHERE {' OR '.join(where)} GROUP BY {group} ORDER BY {group}'''
            for subject,b,a,refs in self.paired(sql,"all dimensional "+modality,dims):
                subject = {"modality": modality, **subject}
                state, obs, note = "context", [], "Unknown units/temporality: raw summary only; no rate or histogram quantile inferred."
                if modality == "metrics":
                    state = metric_shift(b,a)
                    note = "Numeric mean increase; not necessarily harmful. Only registered CPU metrics support node anomaly."
                    if subject["metric"] in ("container.cpu.usage", "k8s.pod.cpu.usage") and subject["service_name"] in self.nodes:
                        obs = [f"node:{subject['service_name']}"]
                        if state == "supports" and a["mean"] - b["mean"] < CONTRACT["cpu_delta"]: state = "not_met"
                    elif state == "supports": state = "context"
                self.record("metric_series_summary",subject,b,a,refs,state,obs,note,"source_native")
                registered = subject["metric"] in ("k8s.container.restarts", "k8s.container.ready", "k8s.deployment.available", "k8s.statefulset.ready_pods")
                if modality == "metrics" and registered and subject["service_name"] in self.nodes:
                    state = "insufficient"
                    if b and a and min(b["n"],a["n"]) >= CONTRACT["min_samples"]:
                        if subject["metric"] == "k8s.container.restarts":
                            state = "supports" if a["maximum"] >= b["maximum"] + 1 else "not_met"
                        else:
                            state = "supports" if b["minimum"] > 0 and a["mean"] <= b["mean"]*.5 else "not_met"
                    self.record("metric_lifecycle_change",subject,b,a,refs,state,[f"node:{subject['service_name']}"],
                                "Same dimensional series: restart counter maximum rises >=1, or mean ready/available count halves from positive baseline. Missing series is not an outage.","count")

    def edge_ids(self, src, dst):
        return f"dependency:{src}->{dst}", f"propagation:{src}->{dst}"

    def boundary_ids(self, src, dst):
        return ["root_boundary", f"node:{src}", f"node:{dst}"] if self.boundary == {src,dst} else []

    def edges_evidence(self):
        for src,dst in self.edges:
            dep, prop = self.edge_ids(src,dst)
            keys = ["client_operation", "server_operation"]
            def sql(w):
                t = f"{w}_traces"
                if not self.store.has(t): return None
                return f'''WITH RECURSIVE ancestry AS (
                  SELECT p.trace_id,p.span_id origin,p.parent_span_id next_id,[p.span_id] visited
                  FROM {t} p WHERE p.service_name={quote(dst)} AND {kind('p','client')}
                  UNION ALL
                  SELECT x.trace_id,x.origin,a.parent_span_id,list_append(x.visited,a.span_id)
                  FROM ancestry x JOIN {t} a ON a.trace_id=x.trace_id AND a.span_id=x.next_id
                  WHERE a.service_name={quote(dst)} AND NOT {kind('a','server')}
                    AND NOT list_contains(x.visited,a.span_id)
                ), caller_servers AS (
                  SELECT x.origin,a.* FROM ancestry x JOIN {t} a
                    ON a.trace_id=x.trace_id AND a.span_id=x.next_id
                  WHERE a.service_name={quote(dst)} AND {kind('a','server')}
                ), pairs AS (
                  SELECT p.trace_id,p.span_id,p.parent_span_id,p.time,p.duration,
                    p.span_name client_operation,c.span_name server_operation,
                    p."attr.http.request.method" client_method,c."attr.http.request.method" server_method,
                    p.duration/1e6 client_ms,c.duration/1e6 server_ms,
                    (cast(p.duration AS DOUBLE)-cast(c.duration AS DOUBLE))/1e6 wait_ms,
                    {err('p')} client_error,{err('c')} server_error,
                    c.time >= p.time AND c.time + c.duration * INTERVAL '1 nanosecond' <= p.time + p.duration * INTERVAL '1 nanosecond' contained
                  FROM {t} p JOIN {t} c ON p.trace_id=c.trace_id AND p.span_id=c.parent_span_id
                  WHERE p.service_name={quote(dst)} AND c.service_name={quote(src)}
                    AND {kind('p','client')} AND {kind('c','server')}
                ), observed AS (
                  SELECT p.*,coalesce({err('a')},false) caller_error,
                    a.duration/1e6 caller_ms,
                    a.time <= p.time AND a.time + a.duration * INTERVAL '1 nanosecond' >= p.time + p.duration * INTERVAL '1 nanosecond' caller_contains
                  FROM pairs p LEFT JOIN caller_servers a ON a.trace_id=p.trace_id AND a.origin=p.span_id
                ) SELECT client_operation,server_operation,count(*) n,
                    list_sort(list_distinct(list(client_method))) client_methods,
                    list_sort(list_distinct(list(server_method))) server_methods,
                    median(client_ms) median_ms,quantile_cont(client_ms,.95) p95_ms,
                    median(server_ms) server_ms,median(wait_ms) wait_ms,
                    count(*) FILTER (WHERE client_error) errors,
                    count(*) FILTER (WHERE client_error AND caller_error AND caller_contains) linked_errors,
                    count(*) FILTER (WHERE caller_contains AND contained AND client_ms>=20 AND client_ms>=caller_ms*.5) dominant_calls,
                    count(*) FILTER (WHERE client_method<>server_method) method_mismatch,
                    min(time) first_time,max(time) last_time
                  FROM observed GROUP BY 1,2 ORDER BY 1,2'''
            # DuckDB intervals have microsecond precision; preserve ns timestamps in comparisons via epoch_ns.
            def portable_sql(w):
                raw = sql(w)
                if raw is None: return None
                raw = raw.replace("c.time + c.duration * INTERVAL '1 nanosecond' <= p.time + p.duration * INTERVAL '1 nanosecond'", "epoch_ns(c.time)::HUGEINT + c.duration <= epoch_ns(p.time)::HUGEINT + p.duration")
                return raw.replace("a.time + a.duration * INTERVAL '1 nanosecond' >= p.time + p.duration * INTERVAL '1 nanosecond'", "epoch_ns(a.time)::HUGEINT + a.duration >= epoch_ns(p.time)::HUGEINT + p.duration")
            pair_found = False
            for group,b,a,refs in self.paired(portable_sql,"exact CLIENT/SERVER binding and nearest same-service caller SERVER ancestor",keys):
                pair_found = True
                subject = {"caller": dst,"callee":src,**group}
                self.record("matched_dependency",subject,b,a,refs,"supports",[dep],"Exact (trace_id, CLIENT span_id = SERVER parent_span_id); kind checked.")
                for field in ("median_ms", "p95_ms", "wait_ms"):
                    self.record("edge_latency_"+field,subject,b,a,refs,increased_latency(b,a,field),self.boundary_ids(src,dst),
                                "Matched caller duration/wait anomaly; does not imply callee local failure.","ms")
                self.record("edge_error_rate",subject,b,a,refs,increased_rate(b,a),self.boundary_ids(src,dst),"Only matched target-specific calls.","fraction")
                self.record("edge_linked_error_increase",subject,b,a,refs,increased_rate(b,a,"linked_errors"),[prop],
                            "Composite witness: exact dependency AND increased calls with errors at CLIENT and containing caller SERVER; compatible with propagation, not proof of causal direction.","fraction")
                latency = increased_latency(b,a)
                state = "supports" if latency == "supports" and a["dominant_calls"] >= CONTRACT["min_events"] and a["dominant_calls"] / a["n"] >= .5 else ("insufficient" if latency == "insufficient" else "not_met")
                self.record("edge_nested_latency",subject,b,a,refs,state,[prop],
                            "Composite witness: median call duration increases AND >=50% calls are temporally nested in caller SERVER and occupy >=50% of its duration; at least 3 events.","ms")
                self.record("edge_method_mismatch",subject,b,a,refs,increased_rate(b,a,"method_mismatch"),self.boundary_ids(src,dst),
                            "CLIENT/SERVER HTTP method mismatch increase within exact pairs.","fraction")
            if not pair_found:
                self.record("matched_dependency",{"caller":dst,"callee":src},None,None,[],"insufficient",[dep],"No matching CLIENT/SERVER pair in supplied windows.")
            self.direct_server_edges(src,dst)
            self.bound_orphans(src,dst)


    def direct_server_edges(self, src, dst):
        dep,prop = self.edge_ids(src,dst)
        def sql(w):
            t=f"{w}_traces"
            if not self.store.has(t): return None
            return f'''SELECT p.span_name caller_operation,c.span_name callee_operation,count(*) n,
                median(c.duration)/1e6 median_ms,median(p.duration)/1e6 caller_ms,
                count(*) FILTER (WHERE {err('c')} AND {err('p')}
                  AND p.time<=c.time AND epoch_ns(p.time)::HUGEINT+p.duration>=epoch_ns(c.time)::HUGEINT+c.duration) linked_errors,
                count(*) FILTER (WHERE p.time<=c.time AND epoch_ns(p.time)::HUGEINT+p.duration>=epoch_ns(c.time)::HUGEINT+c.duration
                  AND c.duration>=p.duration*.5 AND c.duration>=20000000) dominant_calls,
                min(c.time) first_time,max(c.time) last_time
                FROM {t} p JOIN {t} c ON p.trace_id=c.trace_id AND p.span_id=c.parent_span_id
                WHERE p.service_name={quote(dst)} AND c.service_name={quote(src)}
                  AND {kind('p','server')} AND {kind('c','server')}
                GROUP BY 1,2 ORDER BY 1,2'''
        for group,b,a,refs in self.paired(sql,"direct cross-service SERVER parent/child",["caller_operation","callee_operation"]):
            subject={"caller":dst,"callee":src,**group}
            self.record("server_parent_dependency",subject,b,a,refs,"supports",[dep],"Direct cross-service SERVER parent/child (e.g. gateway); no CLIENT span assumed.")
            self.record("server_parent_linked_errors",subject,b,a,refs,increased_rate(b,a,"linked_errors"),[prop],"Increased fraction of nested parent and child SERVER errors; propagation-compatible.")
            state=increased_latency(b,a)
            state="supports" if state=="supports" and a["dominant_calls"]>=3 and a["dominant_calls"]/a["n"]>=.5 else ("insufficient" if state=="insufficient" else "not_met")
            self.record("server_parent_nested_latency",subject,b,a,refs,state,[prop],"Increased callee duration AND >=50% calls occupy >=50% of containing caller SERVER duration, >=3 events.","ms")

    def bound_orphans(self, src, dst):
        dep,prop = self.edge_ids(src,dst)
        def sql(w):
            t,l = f"{w}_traces",f"{w}_logs"
            if not self.store.has(t) or not self.store.has(l): return None
            # Binding is unique per CLIENT using exact trace+span plus contained log time.
            # Hostname must be the callee service itself (optional namespace suffix).
            return f'''WITH bindings AS (
                SELECT p.trace_id,p.span_id,p.parent_span_id,p.time,p.duration,p.span_name,
                  {err('p')} is_error,
                  list_distinct(flatten(list(regexp_extract_all(l.message,'https?://([a-zA-Z0-9_-]+)(?:[.:/]|$)',1)))) hosts
                FROM {t} p JOIN {l} l ON l.trace_id=p.trace_id AND l.span_id=p.span_id
                  AND l.service_name=p.service_name AND l.time>=p.time
                  AND epoch_ns(l.time)::HUGEINT <= epoch_ns(p.time)::HUGEINT+p.duration
                WHERE p.service_name={quote(dst)} AND {kind('p','client')}
                  AND NOT EXISTS (SELECT 1 FROM {t} c WHERE c.trace_id=p.trace_id AND c.parent_span_id=p.span_id AND {kind('c','server')})
                GROUP BY p.trace_id,p.span_id,p.parent_span_id,p.time,p.duration,p.span_name,p."attr.status_code",p."attr.http.response.status_code"
              ) SELECT b.span_name client_operation,count(*) n,count(*) FILTER (WHERE b.is_error) errors,
                  count(*) FILTER (WHERE b.is_error AND {err('a')} AND a.time<=b.time
                    AND epoch_ns(a.time)::HUGEINT+a.duration >= epoch_ns(b.time)::HUGEINT+b.duration) linked_errors,
                  median(b.duration)/1e6 median_ms,min(b.time) first_time,max(b.time) last_time
                FROM bindings b LEFT JOIN {t} a ON a.trace_id=b.trace_id AND a.span_id=b.parent_span_id
                  AND a.service_name={quote(dst)} AND {kind('a','server')}
                WHERE len(b.hosts)=1 AND b.hosts[1]={quote(src)} GROUP BY 1 ORDER BY 1'''
        for group,b,a,refs in self.paired(sql,"uniquely URL-bound orphan calls",["client_operation"]):
            subject = {"caller":dst,"callee":src,**group}
            self.record("url_bound_dependency",subject,b,a,refs,"supports",[dep],"Unique exact URL hostname from logs on same trace AND span within CLIENT duration.")
            # A failure is an observed incident, not necessarily an increase (baseline may have no orphans).
            state = "supports" if a and a["errors"]>=CONTRACT["min_events"] else "insufficient"
            self.record("url_bound_failed_call",subject,b,a,refs,state,self.boundary_ids(src,dst),"At least 3 target-bound failed incident calls; baseline increase not claimed.")
            state = "supports" if a and a["linked_errors"]>=CONTRACT["min_events"] else "insufficient"
            self.record("url_bound_linked_errors",subject,b,a,refs,state,[prop],"At least 3 target-bound failed calls nested in erroneous caller SERVER; association, not causal identification.")

    def build(self):
        self.inventory_tables()
        self.traces()
        self.logs()
        self.metrics()
        self.edges_evidence()
        self.candidates.sort(key=lambda x:x["id"])
        ids = [x["id"] for x in self.candidates]
        if len(ids)!=len(set(ids)): raise ValueError("Duplicate candidate identity")
        clauses = []
        for o in self.obligations:
            evidence = [c["id"] for c in self.candidates if c["verdict"]=="supports" and o["id"] in c["obligation_ids"]]
            clauses.append({**o,"literals":evidence,"status":"covered" if evidence else "open",
                            "gap_reason":None if evidence else "insufficient_evidence_under_rule_contract",
                            "observable":"unknown", "excluded_from_denominator":False})
        used = {i for c in clauses for i in c["literals"]}
        literals = [c for c in self.candidates if c["id"] in used]
        summary = {"n_clauses":len(clauses),"covered":sum(c["status"]=="covered" for c in clauses),
                   "open":sum(c["status"]=="open" for c in clauses),"n_candidates":len(self.candidates),
                   "n_literals":len(literals),"n_queries":len(self.store.queries)}
        summary["coverage_all"] = summary["covered"]/len(clauses) if clauses else None
        cnf = {"schema_version":"2.0", "case":self.case_dir.name,"status":"complete" if not summary["open"] else "needs_review",
               "construction":"deterministic_rule_enumeration", "privileged_offline_artifact":True,
               "rule_contract":CONTRACT, "reference_path":self.gt,"summary":summary,
               "semantics":"AND of obligation clauses; OR of complete composite witnesses within each clause. Empty clause remains false/unresolved; never dropped. Coverage is operational evidence coverage, not proof of injected root cause.",
               "clauses":clauses,"literals":literals}
        manifest = {"case":self.case_dir.name,"gt_sha256":file_hash(self.case_dir/"ground_truth/gt.json"),
                    "sources":self.store.sources,"rule_contract_sha256":digest(CONTRACT),
                    "engine_sha256":{p.name:file_hash(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
                    "inventory":self.inventory,"enumeration_complete_under_contract":True,
                    "limitations":["Not all possible fault mechanisms; only registered rules and observed groups.",
                        "No counter rates or histogram quantiles without temporality metadata.",
                        "No exact injection-mechanism labels inferred from GT.",
                        "Propagation predicates establish request-linked compatibility, not causality.",
                        "Missing tables retained as unavailable; unseen groups cannot be enumerated."]}
        return cnf,{"manifest":manifest,"candidates":self.candidates,"queries":sorted(self.store.queries,key=lambda q:q["id"])}
