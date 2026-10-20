#!/usr/bin/env python3
"""Extract selected cases from the follow-the-trace tar into OpsBench's data layout.

Authoritative sources (both under data/raw/follow-the-trace-artifacts/):
  * follow-the-trace-dataset.tar              telemetry + span-level SLO graph + misc
  * follow-the-trace-dataset-annotations.tar.gz  corrected service-level gt.json (2026-08-16)

The annotations tarball always wins over the gt.json embedded in the main tar
(the main tar is a 5 GB snapshot that is never re-issued for label errata).

Output layout mirrors Aiops_RL so vendored tooling works unchanged:

  data/cases/<case>/telemetry/*.parquet          (10 tables, only thing an agent may see)
  data/cases/<case>/slo_source/causal_graph.json (span-level detector output, offline only)
  data/cases/<case>/slo_source/conclusion.parquet
  data/cases/<case>/ground_truth/gt.json         (corrected human GT, judge only)
  data/cases/<case>/ground_truth/{injection,env,result}.json, label.txt

Usage:
  python -m opsbench.prepare_cases --cases data/index/pilot10.txt
  python -m opsbench.prepare_cases --cases ts2-ts-auth-service-loss-5k6gqr ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "follow-the-trace-artifacts"
CASES = ROOT / "data" / "cases"
DATASET_TAR = RAW / "follow-the-trace-dataset.tar"
ANNOTATIONS_TAR = RAW / "follow-the-trace-dataset-annotations.tar.gz"

TELEMETRY_STEMS = frozenset({
    "normal_logs", "abnormal_logs",
    "normal_traces", "abnormal_traces",
    "normal_metrics", "abnormal_metrics",
    "normal_metrics_histogram", "abnormal_metrics_histogram",
    "normal_metrics_sum", "abnormal_metrics_sum",
})
GT_EXTRA = frozenset({"injection.json", "env.json", "label.txt", "result.json"})
SLO_FILES = frozenset({"causal_graph.json", "conclusion.parquet"})


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_gt(text: bytes) -> str | None:
    gt = json.loads(text)
    if "root_causes" not in gt:
        return "no root_causes"
    comps = [n.get("component", "") for n in gt.get("nodes", [])]
    if comps and not all(c.startswith("service|") for c in comps):
        return f"not service-level: {comps[:2]}"
    return None


def _validate_slo_graph(text: bytes) -> str | None:
    graph = json.loads(text)
    comps = [str(n.get("component", "")) for n in graph.get("nodes", [])]
    if not any(c.startswith("span|") for c in comps):
        return f"SLO graph has no span-level node: {comps[:2]}"
    return None


def _write(dest: Path, data: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def load_case_list(spec: list[str]) -> list[str]:
    if len(spec) == 1 and Path(spec[0]).is_file():
        lines = Path(spec[0]).read_text().splitlines()
        return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    return spec


def read_annotations(case_ids: set[str]) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    with tarfile.open(ANNOTATIONS_TAR, "r:gz") as tar:
        for member in tar:
            if not member.name.endswith("gt.json"):
                continue
            parts = member.name.split("/")
            case_id = parts[1] if len(parts) >= 3 else parts[0]
            if case_id in case_ids:
                out[case_id] = tar.extractfile(member).read()
    return out


def extract_cases(case_ids: list[str], annotations: dict[str, bytes]) -> dict[str, dict]:
    """Single sequential pass over the 5 GB tar; only wanted members are read."""
    wanted = set(case_ids)
    report: dict[str, dict] = {c: {"telemetry": 0, "slo": [], "gt_extra": [], "gt": None} for c in case_ids}
    with tarfile.open(DATASET_TAR, "r") as tar:
        for member in tar:
            if not member.isfile():
                continue
            parts = member.name.split("/")
            if len(parts) != 4 or parts[2] != "converted":
                continue
            case_id, name = parts[1], parts[3]
            if case_id not in wanted:
                continue
            stem = name.rsplit(".", 1)[0]
            data = tar.extractfile(member).read()
            dest = CASES / case_id
            if name.endswith(".parquet") and stem in TELEMETRY_STEMS:
                _write(dest / "telemetry" / name, data)
                report[case_id]["telemetry"] += 1
            elif name in SLO_FILES:
                if name == "causal_graph.json":
                    err = _validate_slo_graph(data)
                    if err:
                        raise ValueError(f"{case_id}: {err}")
                _write(dest / "slo_source" / name, data)
                report[case_id]["slo"].append(name)
            elif name in GT_EXTRA:
                _write(dest / "ground_truth" / name, data)
                report[case_id]["gt_extra"].append(name)
            elif name == "gt.json":
                report[case_id]["gt"] = "embedded"
                if case_id not in annotations:
                    _write(dest / "ground_truth" / name, data)
    for case_id, gt_bytes in annotations.items():
        err = _validate_gt(gt_bytes)
        if err:
            raise ValueError(f"{case_id}: annotation gt.json invalid: {err}")
        _write(CASES / case_id / "ground_truth" / "gt.json", gt_bytes)
        report[case_id]["gt"] = f"annotations:{_sha256(gt_bytes)[:16]}"
    return report


def write_index(case_ids: list[str], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "case_id": c,
            "data_dir": str(CASES / c / "telemetry"),
            "slo_path": str(CASES / c / "slo_source" / "causal_graph.json"),
            "gt_path": str(CASES / c / "ground_truth" / "gt.json"),
        }
        for c in case_ids
    ]
    index_path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="+", required=True, help="case ids or a text file of ids")
    parser.add_argument("--index", default=str(ROOT / "data" / "index" / "pilot10.jsonl"))
    args = parser.parse_args()

    case_ids = load_case_list(args.cases)
    missing = [p for p in (DATASET_TAR, ANNOTATIONS_TAR) if not p.exists()]
    if missing:
        print(f"missing archives: {missing}", file=sys.stderr)
        return 2

    annotations = read_annotations(set(case_ids))
    report = extract_cases(case_ids, annotations)
    failures = []
    for case_id in case_ids:
        r = report[case_id]
        ok = r["telemetry"] == 10 and "causal_graph.json" in r["slo"] and r["gt"]
        print(f"{'ok ' if ok else 'BAD'} {case_id} telemetry={r['telemetry']} slo={sorted(r['slo'])} "
              f"gt={r['gt']} extra={sorted(r['gt_extra'])}")
        if not ok:
            failures.append(case_id)
    write_index(case_ids, Path(args.index))
    print(f"index -> {args.index}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
