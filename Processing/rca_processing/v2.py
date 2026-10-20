"""Read-only adapter to the existing frozen rule enumerator; outputs stay here."""
import sys
from pathlib import Path


def extract(case_dir, project=None):
    project = project or Path(__file__).resolve().parents[2] / "OpsBench_V2"
    sys.path.insert(0, str(project))
    from opsbench_v2.enumerate import Enumerator
    enumerator = Enumerator(case_dir)
    try:
        cnf, artifacts = enumerator.build()
        candidates = enumerator.candidates
        used = {e["id"] for e in cnf["literals"]}
        records = []
        for c in candidates:
            rule = c["rule_id"]
            modality = ("metric" if rule.startswith("metric") else
                        "log" if rule.startswith("log") else "trace")
            records.append({
                "id": c["id"], "method": "v2", "modality": modality, "kind": rule,
                "subject": c["subject"], "observation": c,
                "selected": c["id"] in used, "semantics": "registered_rule_support",
            })
        clauses = [{**c, "candidate_ids": c["literals"]} for c in cnf["clauses"]]
        phi = {"privileged_offline_artifact": True, "clauses": clauses,
               "summary": {"obligations": len(clauses),
                           "candidate_associated": cnf["summary"]["covered"],
                           "covered": cnf["summary"]["covered"], "open": cnf["summary"]["open"]},
               "semantics": cnf["semantics"]}
        return {"evidence": records, "phi": phi, "profile": artifacts["manifest"],
                "queries": enumerator.store.queries}
    finally:
        enumerator.store.close()
