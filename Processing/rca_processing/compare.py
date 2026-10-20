from __future__ import annotations

from collections import Counter

from .common import dumps


def comparison(bundles):
    result = {}
    for name, bundle in bundles.items():
        records = bundle["evidence"]
        selected = [r for r in records if r["selected"]]
        result[name] = {
            "candidate_count": len(records), "selected_count": len(selected),
            "selected_by_modality": dict(Counter(r["modality"] for r in selected)),
            "selected_json_chars": sum(len(dumps(r)) for r in selected),
            "path_obligations": bundle["phi"]["summary"],
            "verification_level": "registered_rules" if name == "v2" else "manual_review_required",
            "extraction_scope": "path" if name == "v2" else bundle["profile"]["scope"],
        }
    return {
        "methods": result,
        "conclusion": "Descriptive comparison only. Candidate association, heuristic rule coverage "
                      "and independently reviewed evidence coverage are different quantities.",
        "precision": None, "recall": None,
        "missing_for_quality_ranking": "Independent evidence validity/completeness adjudication "
                                       "and matched-case evaluation; V2 is not an exhaustive gold set.",
    }
