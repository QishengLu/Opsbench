"""FoundRoot k-sigma detector adapted to paired RCABench windows, no GT filtering."""
from __future__ import annotations

import numpy as np

from .common import evidence, series_rows


def extract(data, k=4.0, min_reference=3):
    if k <= 0 or min_reference < 2:
        raise ValueError("Invalid k-sigma configuration")
    records = []
    for subject, group in data.metric_series():
        normal = group[group["_window"] == "normal"]["value"].astype(float)
        normal = normal[np.isfinite(normal)]
        incident = group[group["_window"] == "abnormal"]["value"].astype(float)
        incident = incident[np.isfinite(incident)]
        mean, std = normal.mean(), normal.std(ddof=1)
        valid = len(normal) >= min_reference and np.isfinite(std) and std > 0
        selected = valid and len(incident) > 0 and bool(
            ((incident - mean).abs() > k * std).any()
        )
        verdict = "anomaly" if selected else "not_flagged" if valid else "insufficient_baseline"
        records.append(evidence(
            "foundroot", "metric", "metric_series", subject,
            {"baseline_n": len(normal), "baseline_mean": mean, "baseline_std": std,
             "k": k, "verdict": verdict,
             "series": series_rows(group) if selected else [],
             "source_selector": "all rows matching every subject dimension in both windows"},
            selected=selected,
        ))
    return records, {
        "profile": "foundroot-rcabench-adaptation", "k": k, "min_reference": min_reference,
        "histograms": "excluded: original processor takes scalar metrics",
        "differences": [
            "RCABench supplied normal window replaces DejaVu contiguous pre-trigger segment.",
            "K=4 and minimum=3 follow the public script's explicitly speculative defaults.",
            "No known-root retention, case exclusion, metric subsampling, or zero padding.",
            "Preserve actual timestamps and all dimensions; no 60-second resampling.",
            "No log/trace anomaly detection is attributed to FoundRoot.",
        ],
    }
