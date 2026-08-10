from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IN_DIR = ROOT / "06_experiment_inputs"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-month", default="2015-06")
    parser.add_argument("--end-month", default="2024-07")
    args = parser.parse_args()

    source = IN_DIR / "monthly_topic_impact_long.csv"
    df = pd.read_csv(source, dtype={"month": "string"})

    mask = (df["month"] >= args.start_month) & (df["month"] <= args.end_month)
    filtered = df.loc[mask].copy()
    filtered = filtered.sort_values(["stakeholder", "month", "topic_id"])

    suffix = f"{args.start_month}_{args.end_month}"
    long_path = IN_DIR / f"monthly_topic_impact_common_window_{suffix}.csv"
    filtered.to_csv(long_path, index=False)

    outputs = {"long": str(long_path)}
    for stakeholder, sdf in filtered.groupby("stakeholder", observed=True):
        wide_abs = sdf.pivot_table(
            index="month",
            columns="topic_id",
            values="absolute_impact",
            aggfunc="sum",
            fill_value=0,
        )
        wide_abs.columns = [f"topic_{int(col)}" for col in wide_abs.columns]
        abs_path = IN_DIR / f"{stakeholder}_monthly_topic_absolute_common_window_{suffix}.csv"
        wide_abs.reset_index().to_csv(abs_path, index=False)
        outputs[f"{stakeholder}_absolute_wide"] = str(abs_path)

        wide_rel = sdf.pivot_table(
            index="month",
            columns="topic_id",
            values="relative_impact",
            aggfunc="sum",
            fill_value=0,
        )
        wide_rel.columns = [f"topic_{int(col)}" for col in wide_rel.columns]
        rel_path = IN_DIR / f"{stakeholder}_monthly_topic_relative_common_window_{suffix}.csv"
        wide_rel.reset_index().to_csv(rel_path, index=False)
        outputs[f"{stakeholder}_relative_wide"] = str(rel_path)

    diagnostics = {
        "source": str(source),
        "start_month": args.start_month,
        "end_month": args.end_month,
        "outputs": outputs,
        "rows": int(len(filtered)),
        "by_stakeholder": {},
    }

    for stakeholder, sdf in filtered.groupby("stakeholder", observed=True):
        monthly_sums = sdf.groupby("month", observed=True)["relative_impact"].sum()
        diagnostics["by_stakeholder"][stakeholder] = {
            "months": int(sdf["month"].nunique()),
            "month_min": str(sdf["month"].min()),
            "month_max": str(sdf["month"].max()),
            "topic_count": int(sdf["topic_id"].nunique()),
            "absolute_impact_sum": int(sdf["absolute_impact"].sum()),
            "relative_impact_monthly_sum_min": float(monthly_sums.min()),
            "relative_impact_monthly_sum_max": float(monthly_sums.max()),
        }

    diag_path = IN_DIR / f"monthly_topic_impact_common_window_{suffix}_diagnostics.json"
    diag_path.write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    main()
