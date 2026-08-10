from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "06_experiment_inputs"

USER_FINAL_TOPIC_DIR = Path(r"D:\EMSE\Data\JSS\User\ReTopic\Reviews\Final")
DEVELOPER_FINAL_TOPIC_DIR = Path(r"D:\EMSE\Data\JSS\Developer\Developer_lda_topics")
DEVELOPER_RAW = ROOT / "01_public_raw" / "Developer_posts.csv"
DEVELOPER_LABELS = Path(r"D:\EMSE\Data\JSS\Developer\merged_output.csv")


def parse_dates(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    parsed = pd.to_datetime(numeric, errors="coerce", unit="s")
    remaining = parsed.isna() & series.notna()
    if remaining.any():
        parsed.loc[remaining] = pd.to_datetime(series.loc[remaining], errors="coerce")
    return parsed


def clean_id(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def count_csv_rows(path: Path) -> int:
    total = 0
    for chunk in pd.read_csv(path, usecols=[0], chunksize=200_000, encoding_errors="replace"):
        total += len(chunk)
    return total


def load_developer_label_by_count() -> tuple[dict[int, dict], list[dict]]:
    labels = pd.read_csv(DEVELOPER_LABELS, encoding_errors="replace")
    labels = labels.copy()
    labels["Values"] = pd.to_numeric(labels["Values"], errors="coerce").astype("Int64")

    rows_by_value: dict[int, list[dict]] = defaultdict(list)
    for _, row in labels.iterrows():
        rows_by_value[int(row["Values"])].append(row.to_dict())

    mapping: dict[int, dict] = {}
    audit: list[dict] = []
    for file in sorted(DEVELOPER_FINAL_TOPIC_DIR.glob("topic_*.csv"), key=lambda p: int(re.search(r"\d+", p.stem).group())):
        topic_id = int(re.search(r"\d+", file.stem).group())
        row_count = count_csv_rows(file)
        candidates = rows_by_value.get(row_count, [])
        if candidates:
            label_row = candidates.pop(0)
            mapping[topic_id] = {
                "topic_label": str(label_row.get("Merged_GPT_Label2") or label_row.get("GPT_Label2") or label_row.get("GPT_Label")),
                "original_gpt_label": str(label_row.get("GPT_Label")),
                "keywords": str(label_row.get("Keywords")),
                "row_count_expected": row_count,
            }
            status = "matched_by_values"
        else:
            mapping[topic_id] = {
                "topic_label": f"Developer Topic {topic_id}",
                "original_gpt_label": "",
                "keywords": "",
                "row_count_expected": row_count,
            }
            status = "unmatched"
        audit.append(
            {
                "developer_final_topic_id": topic_id,
                "file": str(file),
                "row_count": row_count,
                "assigned_label": mapping[topic_id]["topic_label"],
                "match_status": status,
            }
        )
    return mapping, audit


def aggregate_user_final_topics(min_date: pd.Timestamp, max_date: pd.Timestamp) -> tuple[pd.DataFrame, list[dict]]:
    records: list[pd.DataFrame] = []
    audit: list[dict] = []
    for topic_id, file in enumerate(sorted(USER_FINAL_TOPIC_DIR.glob("*.csv"), key=lambda p: p.name.lower())):
        label = file.stem
        chunks: list[pd.DataFrame] = []
        total_rows = 0
        valid_rows = 0
        invalid_rows = 0
        out_of_range_rows = 0
        for chunk in pd.read_csv(
            file,
            usecols=["review_date"],
            chunksize=200_000,
            encoding_errors="replace",
            low_memory=False,
            on_bad_lines="warn",
        ):
            total_rows += len(chunk)
            dates = parse_dates(chunk["review_date"])
            invalid_rows += int(dates.isna().sum())
            plausible = dates.notna() & dates.between(min_date, max_date, inclusive="both")
            out_of_range_rows += int((dates.notna() & ~plausible).sum())
            valid_rows += int(plausible.sum())
            if plausible.any():
                chunks.append(pd.DataFrame({"month": dates.loc[plausible].dt.to_period("M").astype(str)}))
        if chunks:
            counts = pd.concat(chunks, ignore_index=True).groupby("month").size().reset_index(name="absolute_impact")
            counts["stakeholder"] = "user"
            counts["topic_id"] = topic_id
            counts["topic_label"] = label
            records.append(counts)
        audit.append(
            {
                "stakeholder": "user",
                "topic_id": topic_id,
                "topic_label": label,
                "file": str(file),
                "rows": total_rows,
                "valid_rows": valid_rows,
                "invalid_date_rows": invalid_rows,
                "out_of_range_date_rows": out_of_range_rows,
            }
        )
    return pd.concat(records, ignore_index=True), audit


def load_developer_dates() -> pd.DataFrame:
    dates = pd.read_csv(
        DEVELOPER_RAW,
        usecols=["PostID", "CreationDate"],
        dtype={"PostID": "string"},
        encoding_errors="replace",
        low_memory=False,
        on_bad_lines="warn",
    )
    dates["PostID"] = clean_id(dates["PostID"])
    dates = dates.dropna(subset=["PostID"]).drop_duplicates(subset=["PostID"], keep="first")
    return dates


def aggregate_developer_final_topics(min_date: pd.Timestamp, max_date: pd.Timestamp) -> tuple[pd.DataFrame, list[dict], list[dict]]:
    label_map, label_audit = load_developer_label_by_count()
    date_lookup = load_developer_dates()
    records: list[pd.DataFrame] = []
    audit: list[dict] = []

    for file in sorted(DEVELOPER_FINAL_TOPIC_DIR.glob("topic_*.csv"), key=lambda p: int(re.search(r"\d+", p.stem).group())):
        topic_id = int(re.search(r"\d+", file.stem).group())
        label_info = label_map[topic_id]
        total_rows = 0
        matched_rows = 0
        valid_rows = 0
        invalid_rows = 0
        out_of_range_rows = 0
        chunks: list[pd.DataFrame] = []

        for chunk in pd.read_csv(
            file,
            usecols=["PostID"],
            dtype={"PostID": "string"},
            chunksize=200_000,
            encoding_errors="replace",
            low_memory=False,
            on_bad_lines="warn",
        ):
            total_rows += len(chunk)
            chunk["PostID"] = clean_id(chunk["PostID"])
            merged = chunk.merge(date_lookup, on="PostID", how="left")
            matched_rows += int(merged["CreationDate"].notna().sum())
            dates = parse_dates(merged["CreationDate"])
            invalid_rows += int(dates.isna().sum())
            plausible = dates.notna() & dates.between(min_date, max_date, inclusive="both")
            out_of_range_rows += int((dates.notna() & ~plausible).sum())
            valid_rows += int(plausible.sum())
            if plausible.any():
                chunks.append(pd.DataFrame({"month": dates.loc[plausible].dt.to_period("M").astype(str)}))

        if chunks:
            counts = pd.concat(chunks, ignore_index=True).groupby("month").size().reset_index(name="absolute_impact")
            counts["stakeholder"] = "developer"
            counts["topic_id"] = topic_id
            counts["topic_label"] = label_info["topic_label"]
            records.append(counts)
        audit.append(
            {
                "stakeholder": "developer",
                "topic_id": topic_id,
                "topic_label": label_info["topic_label"],
                "file": str(file),
                "rows": total_rows,
                "matched_date_rows": matched_rows,
                "valid_rows": valid_rows,
                "invalid_date_rows": invalid_rows,
                "out_of_range_date_rows": out_of_range_rows,
            }
        )
    return pd.concat(records, ignore_index=True), audit, label_audit


def add_relative_impact(df: pd.DataFrame) -> pd.DataFrame:
    totals = (
        df.groupby(["stakeholder", "month"], observed=True)["absolute_impact"]
        .sum()
        .reset_index(name="monthly_document_count")
    )
    out = df.merge(totals, on=["stakeholder", "month"], how="left")
    out["relative_impact"] = out["absolute_impact"] / out["monthly_document_count"]
    return out[
        [
            "stakeholder",
            "month",
            "topic_id",
            "topic_label",
            "absolute_impact",
            "relative_impact",
            "monthly_document_count",
        ]
    ].sort_values(["stakeholder", "month", "topic_label"])


def write_wide(df: pd.DataFrame, suffix: str) -> dict[str, str]:
    outputs = {}
    for stakeholder, sdf in df.groupby("stakeholder", observed=True):
        for value_col, label in [("absolute_impact", "absolute"), ("relative_impact", "relative")]:
            wide = sdf.pivot_table(
                index="month",
                columns="topic_label",
                values=value_col,
                aggfunc="sum",
                fill_value=0,
            )
            path = OUT_DIR / f"{stakeholder}_final_topic_{label}_{suffix}.csv"
            wide.reset_index().to_csv(path, index=False)
            outputs[f"{stakeholder}_{label}_wide"] = str(path)
    return outputs


def summarize(df: pd.DataFrame) -> dict:
    summary = {}
    for stakeholder, sdf in df.groupby("stakeholder", observed=True):
        sums = sdf.groupby("month", observed=True)["relative_impact"].sum()
        summary[stakeholder] = {
            "months": int(sdf["month"].nunique()),
            "month_min": str(sdf["month"].min()),
            "month_max": str(sdf["month"].max()),
            "topic_count": int(sdf["topic_label"].nunique()),
            "absolute_impact_sum": int(sdf["absolute_impact"].sum()),
            "relative_impact_monthly_sum_min": float(sums.min()),
            "relative_impact_monthly_sum_max": float(sums.max()),
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-month", default="2015-06")
    parser.add_argument("--end-month", default="2024-07")
    args = parser.parse_args()

    min_date = pd.Timestamp(f"{args.start_month}-01")
    max_date = pd.Period(args.end_month, freq="M").end_time
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    user_df, user_audit = aggregate_user_final_topics(min_date, max_date)
    developer_df, developer_audit, developer_label_audit = aggregate_developer_final_topics(min_date, max_date)

    monthly = add_relative_impact(pd.concat([user_df, developer_df], ignore_index=True))
    suffix = f"common_window_{args.start_month}_{args.end_month}"
    long_path = OUT_DIR / f"monthly_final_topic_impact_{suffix}.csv"
    monthly.to_csv(long_path, index=False)
    outputs = {"long": str(long_path)}
    outputs.update(write_wide(monthly, suffix))

    inventory = pd.concat(
        [
            pd.DataFrame(user_audit)[["stakeholder", "topic_id", "topic_label", "rows", "valid_rows"]],
            pd.DataFrame(developer_audit)[["stakeholder", "topic_id", "topic_label", "rows", "valid_rows"]],
        ],
        ignore_index=True,
    )
    inventory_path = OUT_DIR / f"final_topic_inventory_{suffix}.csv"
    inventory.to_csv(inventory_path, index=False)
    outputs["topic_inventory"] = str(inventory_path)

    diagnostics = {
        "start_month": args.start_month,
        "end_month": args.end_month,
        "outputs": outputs,
        "summary": summarize(monthly),
        "user_topic_audit": user_audit,
        "developer_topic_audit": developer_audit,
        "developer_label_matching_audit": developer_label_audit,
    }
    diag_path = OUT_DIR / f"monthly_final_topic_impact_{suffix}_diagnostics.json"
    diag_path.write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    print(json.dumps({"outputs": outputs, "summary": diagnostics["summary"]}, indent=2))


if __name__ == "__main__":
    main()
