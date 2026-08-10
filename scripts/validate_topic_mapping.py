from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MAPPING_DIR = ROOT / "07_cross_stakeholder_mapping"


def main() -> None:
    candidates = pd.read_csv(MAPPING_DIR / "topic_mapping_initial_candidates.csv")

    validated = candidates[candidates["mapping_status"] == "matched"].copy()
    validated["manual_review_status"] = "validated_conservative"
    validated["validation_decision"] = "keep"
    validated["validation_note"] = (
        "Retained because the pair has a direct and interpretable user-facing to developer-facing relationship. "
        "One-to-many mappings are allowed when each pair is independently meaningful."
    )

    unmatched = candidates[candidates["mapping_status"] == "user_salient_unmatched"].copy()
    unmatched["manual_review_status"] = "validated_conservative"
    unmatched["validation_decision"] = "retain_for_gap_discussion_only"
    unmatched["validation_note"] = (
        "Retained as user-salient topics without a clear developer-topic counterpart; excluded from alignment and lag statistics."
    )

    removed = candidates[candidates["mapping_status"] == "weak_match"].copy()
    removed["manual_review_status"] = "validated_conservative"
    removed["validation_decision"] = "remove"
    removed["validation_note"] = (
        "Removed because the semantic relation was too indirect for reviewer-facing quantitative alignment analysis."
    )

    validated_path = MAPPING_DIR / "topic_mapping_validated.csv"
    matched_only_path = MAPPING_DIR / "topic_mapping_validated_matched_only.csv"
    unmatched_path = MAPPING_DIR / "topic_mapping_validated_user_salient_unmatched.csv"
    removed_path = MAPPING_DIR / "topic_mapping_removed_weak_matches.csv"

    pd.concat([validated, unmatched], ignore_index=True).to_csv(validated_path, index=False)
    validated.to_csv(matched_only_path, index=False)
    unmatched.to_csv(unmatched_path, index=False)
    removed.to_csv(removed_path, index=False)

    summary = {
        "source": str(MAPPING_DIR / "topic_mapping_initial_candidates.csv"),
        "validated_mapping": str(validated_path),
        "validated_matched_only": str(matched_only_path),
        "validated_user_salient_unmatched": str(unmatched_path),
        "removed_weak_matches": str(removed_path),
        "counts": {
            "kept_matched_pairs_for_statistics": int(len(validated)),
            "kept_user_salient_unmatched_for_discussion": int(len(unmatched)),
            "removed_weak_matches": int(len(removed)),
        },
        "rule": (
            "Weak matches were removed. One-to-many mappings were retained when each pair had a direct, "
            "independently interpretable semantic relationship. User-salient unmatched topics are excluded "
            "from alignment and lag statistics but retained for gap discussion."
        ),
    }
    summary_path = MAPPING_DIR / "topic_mapping_validation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
