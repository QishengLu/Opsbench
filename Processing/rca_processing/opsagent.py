"""RCABench adaptation of pinned OpsAgent detector/filtering semantics."""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from sklearn.feature_extraction.text import TfidfVectorizer

from .common import evidence


def metric_features(data, classifier):
    output, patterns = [], defaultdict(list)
    pod_scores, metric_scores = Counter(), Counter()
    subjects = {}
    for subject, group in data.metric_series():
        group = group[np.isfinite(group["value"])].reset_index(drop=True)
        values = group["value"].to_numpy(dtype=float)
        if len(values) < 2:
            continue
        std = np.std(values, ddof=1)
        if not np.isfinite(std) or std <= 0:
            continue
        scores = np.abs(values - np.mean(values)) / std
        pod = subject.get("attr.k8s.pod.name") or subject.get("service_name") or "unknown"
        for pos in np.flatnonzero(scores > 3):
            row = group.iloc[pos]
            pod_scores[pod] += float(scores[pos])
            metric_scores[(pod, subject.get("metric"))] += float(scores[pos])
            start, end = max(0, pos - 20), min(len(values), pos + 10)
            if end - start < 30:
                pad = 30 - (end - start)
                if start > pad:
                    start -= pad
                else:
                    end = min(len(values), end + pad)
            label = classifier.predict(values[start:end]) if end - start == 30 else None
            item = evidence("opsagent", "metric", "metric_anomaly", subject,
                            {"time": row["time"], "window": row["_window"],
                             "source_row": int(row["_source_row"]), "value": row["value"],
                             "z_score": scores[pos], "pattern": label,
                             "mean": np.mean(values), "std": std},
                            selected=False, selection_reason="requires_shape_and_group_ranking")
            output.append(item)
            if label is not None:
                # Preserve dimension identity instead of merging different physical series.
                key = (tuple((k, str(v)) for k, v in sorted(subject.items())), label)
                subjects[key] = subject
                patterns[key].append(item)
    groups = sorted(patterns.values(), key=lambda items: (-max(
        x["observation"]["z_score"] for x in items), items[0]["id"]))
    for rank, items in enumerate(groups):
        maximum = max(x["observation"]["z_score"] for x in items)
        keep = rank < 24 and not (len(items) > 10 and maximum < 6)
        for item in items:
            item["selected"] = keep
            item["selection_reason"] = "retained_group" if keep else "rank_or_frequent_weak_group"
    top_pods = [pod for pod, _ in pod_scores.most_common(5)]
    metric_totals = Counter()
    for (pod, metric), score in metric_scores.items():
        if pod in top_pods:
            metric_totals[metric] += score
    return output, {"top5_pods": top_pods, "top5_metrics": metric_totals.most_common(5)}


def log_features(data):
    frame = data.table("abnormal", "logs")
    if frame.empty:
        return []
    frame = frame.sort_values(["time", "_source_row"], kind="stable").copy()
    miner = TemplateMiner(config=TemplateMinerConfig())
    frame["_template"] = [
        miner.add_log_message(str(message))["template_mined"]
        for message in frame["message"].fillna("")
    ]
    # The upstream implementation requests log_template; drain3 0.9.11 returns
    # template_mined. We use its actual template output and record this correction.
    mask = frame["message"].str.contains("failure|fail|failed|error|fatal|crash", case=False, na=False)
    if not mask.any():
        return []
    vectorizer = TfidfVectorizer(binary=True, use_idf=True, smooth_idf=True,
                                norm=None, stop_words="english")
    try:
        vectorizer.fit(frame["_template"].tolist())
        scores = np.asarray(vectorizer.transform(frame.loc[mask, "_template"]).mean(axis=1)).ravel()
    except ValueError:  # Empty vocabulary: no useful lexical evidence.
        return []
    filtered = frame.loc[mask].copy()
    filtered["_score"] = scores
    threshold = filtered["_score"].quantile(.8)
    seen, output = set(), []
    for row in filtered.to_dict("records"):
        minute = int(row["time"].timestamp()) // 60
        # Preserve upstream global template/minute deduplication, including cross-service drops.
        key = (minute, row["_template"])
        priority = row["_score"] >= threshold
        selected = priority and key not in seen
        if priority:
            seen.add(key)
        output.append(evidence(
            "opsagent", "log", "log_template",
            {"service_name": row.get("service_name"), "template": row["_template"]},
            {"time": row["time"], "source_row": row["_source_row"], "window": "abnormal",
             "message": row["message"], "level": row.get("level"),
             "trace_id": row.get("trace_id"), "span_id": row.get("span_id"),
             "priority": row["_score"], "threshold": threshold},
            selected=selected,
            selection_reason="retained" if selected else "priority_or_minute_template_dedup",
        ))
    return output


def trace_features(data, quantile=.98):
    frame = data.table("abnormal", "traces")
    if frame.empty:
        return []
    frame = frame.copy()
    if frame.duplicated(["trace_id", "span_id"]).any():
        raise ValueError("Nonunique trace/span identity")
    types = ["service_name", "span_name", "attr.span_kind"]
    threshold = frame.groupby(types, dropna=False)["duration"].transform(
        lambda x: x.quantile(quantile)
    )
    slow = frame[frame["duration"] > threshold]
    by_id = {(r["trace_id"], r["span_id"]): r for r in frame.to_dict("records")}
    windows, paths = defaultdict(list), defaultdict(list)
    for row in slow.to_dict("records"):
        parent = by_id.get((row["trace_id"], row.get("parent_span_id")))
        grandparent = by_id.get((row["trace_id"], parent.get("parent_span_id"))) if parent else None
        caller = parent["service_name"] if parent else None
        event = {"trace_id": row["trace_id"], "span_id": row["span_id"],
                 "parent_span_id": row.get("parent_span_id"), "source_row": row["_source_row"],
                 "time": row["time"], "duration_ms": row["duration"] / 1e6, "caller": caller}
        windows[(int(row["time"].timestamp()) // 60, row["service_name"])].append(event)
        if grandparent and parent:
            paths[(grandparent["service_name"], caller, row["service_name"])].append(event)
    output = []
    ranked = sorted(windows.items(), key=lambda x: (
        -len(x[1]), -max(e["duration_ms"] for e in x[1]), str(x[0])
    ))
    for rank, ((minute, callee), entries) in enumerate(ranked):
        output.append(evidence(
            "opsagent", "trace", "high_latency_window", {"service_name": callee},
            {"start_epoch": minute * 60, "end_epoch": minute * 60 + 60,
             "count": len(entries), "max_latency_ms": max(e["duration_ms"] for e in entries),
             "callers": dict(Counter(e["caller"] or "unknown" for e in entries)),
             "events": entries}, selected=rank < 24, selection_reason="top24_window" if rank < 24 else "window_rank",
        ))
    ranked_paths = sorted(paths.items(), key=lambda x: (-len(x[1]), str(x[0])))
    eligible = [(p, e) for p, e in ranked_paths if len(e) >= 2]
    for rank, (path, entries) in enumerate(eligible):
        output.append(evidence(
            "opsagent", "trace", "three_hop_path", {"path": list(path)},
            {"count": len(entries), "events": entries}, selected=rank < 24,
            selection_reason="top24_path" if rank < 24 else "path_rank",
        ))
    return output


def extract(data, classifier, quantile=.98):
    metrics, summary = metric_features(data, classifier)
    logs = log_features(data)
    traces = trace_features(data, quantile)
    return metrics + logs + traces, {
        "profile": "opsagent-public-code-rcabench-adaptation",
        "trace_quantile": quantile, "metric_ranking": summary,
        "differences": [
            "Pinned public code uses whole supplied series mean/std, not sliding-window sigma.",
            "Default trace q=.98 follows public code; paper v1 says .95. Both configurable.",
            "Top-5 pods/metrics are descriptions in public code, not hard filters; top24 shape groups are retained.",
            "Metrics use paired normal+abnormal windows; logs and traces use incident window.",
            "All metric dimensions remain separate; missing values are not filled with zero.",
            "Use actual Drain3 template_mined field instead of upstream log_template fallback.",
            "Span links keyed by (trace_id,span_id), missing caller remains unknown, ns converted to ms.",
            "60-second bucket end corrected from upstream +30 to +60.",
            "Histogram metrics omitted; retained raw observations are audit extensions.",
        ],
    }
