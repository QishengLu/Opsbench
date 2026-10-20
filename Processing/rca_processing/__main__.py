from __future__ import annotations

import argparse
import json
import importlib.metadata
import sys
from pathlib import Path

from .alignment import align, component, dimacs
from .common import DEFAULT_INDEX, FOUND_COMMIT, OPS_COMMIT, Dataset, dumps, hash_file
from .compare import comparison


def write(path, value):
    path.write_text(dumps(value) + "\n")


def main():
    p = argparse.ArgumentParser(description="Build offline evidence for the shared 500-case RCABench")
    p.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    p.add_argument("--case", help="One case ID; otherwise first --limit cases in frozen index order")
    p.add_argument("--limit", type=int, default=1)
    p.add_argument("--methods", default="foundroot,opsagent,v2")
    p.add_argument("--scope", choices=["global", "path"], default="global",
                   help="global: detect then align; path: privileged GT-scoped offline extraction")
    p.add_argument("--output", type=Path, required=True, help="New run directory")
    p.add_argument("--shape-checkpoint", type=Path,
                   default=Path(__file__).resolve().parents[1] / "assets/patterncla.pt")
    p.add_argument("--k", type=float, default=4)
    p.add_argument("--trace-quantile", type=float, default=.98)
    p.add_argument("--reviews", type=Path, help="JSON: case_id -> method -> obligation -> evidence_id -> verdict")
    args = p.parse_args()
    methods = args.methods.split(",")
    if set(methods) - {"foundroot", "opsagent", "v2"} or len(methods) != len(set(methods)):
        p.error("methods must be a unique subset of foundroot,opsagent,v2")
    if args.limit < 1 or args.k <= 0 or not 0 < args.trace_quantile < 1:
        p.error("Invalid processing parameters")
    if args.output.exists():
        p.error("Run directory exists; use a new output directory")
    classifier = None
    if "opsagent" in methods:
        if not args.shape_checkpoint.is_file():
            p.error("OpsAgent shape weights missing; run python -m rca_processing.fetch_assets")
        from .shapes import ShapeClassifier
        classifier = ShapeClassifier(args.shape_checkpoint)
    rows = [json.loads(line) for line in args.index.read_text().splitlines() if line.strip()]
    rows = [r for r in rows if r["case_id"] == args.case] if args.case else rows[:args.limit]
    if not rows:
        p.error("No matching cases")
    reviews = json.loads(args.reviews.read_text()) if args.reviews else {}
    args.output.mkdir(parents=True)
    run = {"dataset_index_sha256": hash_file(args.index), "methods": methods,
           "scope": args.scope, "v2_scope": "path",
           "opsagent_commit": OPS_COMMIT, "foundroot_commit": FOUND_COMMIT,
           "case_ids": [r["case_id"] for r in rows], "status": "running",
           "source_code": {p.name: hash_file(p) for p in Path(__file__).parent.glob("*.py")},
           "shape_checkpoint_sha256": hash_file(args.shape_checkpoint) if classifier else None,
           "python": sys.version,
           "dependencies": {name: importlib.metadata.version(name) for name in
                            ["numpy", "pandas", "pyarrow", "scikit-learn", "duckdb", "drain3"]}}
    write(args.output / "run.json", run)
    summaries = {}
    try:
        for row in rows:
            root = args.index.resolve().parent
            telemetry = (root / row["data_dir"]).resolve()
            gt_path = root / row["gt_path"]
            gt = json.loads(gt_path.read_text()) if args.scope == "path" else None
            scope = {component(n["component"]) for n in gt["nodes"]} if gt else None
            data = Dataset(telemetry, scope)
            bundles = {}
            # Global mode completes detection before loading corrected GT.
            # Path mode is explicitly privileged and never an online input.
            for method in methods:
                if method == "foundroot":
                    from .foundroot import extract
                    records, profile = extract(data, args.k)
                elif method == "opsagent":
                    from .opsagent import extract
                    records, profile = extract(data, classifier, args.trace_quantile)
                else:
                    continue
                profile["scope"] = args.scope
                profile["privileged_extraction"] = args.scope == "path"
                bundles[method] = {"evidence": records, "profile": profile}
            gt = gt if gt is not None else json.loads(gt_path.read_text())
            for method, bundle in bundles.items():
                bundle["phi"] = align(bundle["evidence"], gt,
                                      reviews.get(row["case_id"], {}).get(method))
            if "v2" in methods:
                from .v2 import extract
                bundles["v2"] = extract(telemetry.parent)
            case_output = args.output / row["case_id"]
            case_output.mkdir()
            write(case_output / "provenance.json",
                  {"telemetry": data.provenance(), "gt_sha256": hash_file(gt_path)})
            for method, bundle in bundles.items():
                folder = case_output / method
                folder.mkdir()
                with (folder / "candidates.jsonl").open("w") as f:
                    for record in bundle["evidence"]:
                        f.write(dumps(record) + "\n")
                path_ids = {eid for clause in bundle["phi"]["clauses"]
                            for eid in clause["candidate_ids"] + clause["literals"]}
                with (folder / "path_evidence.jsonl").open("w") as f:
                    for record in bundle["evidence"]:
                        if record["id"] in path_ids:
                            f.write(dumps(record) + "\n")
                write(folder / "phi.json", bundle["phi"])
                cnf, variables = dimacs(bundle["phi"])
                (folder / "phi.cnf").write_text(cnf)
                write(folder / "variables.json", variables)
                write(folder / "profile.json", bundle["profile"])
                if "queries" in bundle:
                    write(folder / "queries.json", bundle["queries"])
            report = comparison(bundles)
            write(case_output / "comparison.json", report)
            summaries[row["case_id"]] = report
            print(dumps({"case": row["case_id"], "methods": report["methods"]}), flush=True)
        run["status"] = "completed"
    except Exception as exc:
        run["status"], run["error"] = "failed", f"{type(exc).__name__}: {exc}"
        raise
    finally:
        write(args.output / "run.json", run)
        write(args.output / "summary.json", summaries)


if __name__ == "__main__":
    main()
