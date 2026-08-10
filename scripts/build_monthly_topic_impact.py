from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "01_public_raw"
TOPIC_DIR = ROOT / "02_final_topic_assignments"
OUT_DIR = ROOT / "06_experiment_inputs"


def clean_id(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def load_topic_assignments(path: Path, id_col: str) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(
        path,
        usecols=[id_col, "Dominant_Topic"],
        dtype={id_col: "string"},
        encoding_errors="replace",
        low_memory=False,
    )
    original_rows = len(df)
    df[id_col] = clean_id(df[id_col])
    df = df.dropna(subset=[id_col, "Dominant_Topic"])
    df["Dominant_Topic"] = pd.to_numeric(df["Dominant_Topic"], errors="coerce")
    df = df.dropna(subset=["Dominant_Topic"])
    df["Dominant_Topic"] = df["Dominant_Topic"].astype("int64")
    duplicate_rows = int(df.duplicated(subset=[id_col]).sum())
    df = df.drop_duplicates(subset=[id_col], keep="first")
    stats = {
        "topic_assignment_file": str(path),
        "topic_assignment_rows": int(original_rows),
        "topic_assignment_rows_after_cleaning": int(len(df)),
        "topic_assignment_duplicate_ids_dropped": duplicate_rows,
        "topic_count": int(df["Dominant_Topic"].nunique()),
    }
    return df, stats


def parse_dates(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    parsed = pd.to_datetime(numeric, errors="coerce", unit="s")

    remaining = parsed.isna() & series.notna()
    if remaining.any():
        parsed.loc[remaining] = pd.to_datetime(series.loc[remaining], errors="coerce")
    return parsed


def aggregate_monthly(
    *,
    stakeholder: str,
    raw_path: Path,
    topic_path: Path,
    id_col: str,
    date_col: str,
    chunksize: int,
    min_date: pd.Timestamp,
    max_date: pd.Timestamp,
) -> tuple[pd.DataFrame, dict]:
    topics, stats = load_topic_assignments(topic_path, id_col)
    total_raw_rows = 0
    matched_topic_rows = 0
    valid_date_rows = 0
    invalid_date_rows = 0
    out_of_range_date_rows = 0
    counts: list[pd.DataFrame] = []
    monthly_totals: list[pd.DataFrame] = []

    for chunk in pd.read_csv(
        raw_path,
        usecols=[id_col, date_col],
        dtype={id_col: "string"},
        chunksize=chunksize,
        encoding_errors="replace",
        low_memory=False,
        on_bad_lines="warn",
    ):
        total_raw_rows += len(chunk)
        chunk[id_col] = clean_id(chunk[id_col])
        merged = chunk.merge(topics, on=id_col, how="inner")
        matched_topic_rows += len(merged)

        parsed_dates = parse_dates(merged[date_col])
        invalid_date_rows += int(parsed_dates.isna().sum())
        plausible_dates = parsed_dates.notna() & parsed_dates.between(min_date, max_date, inclusive="both")
        out_of_range_date_rows += int((parsed_dates.notna() & ~plausible_dates).sum())
        merged = merged.loc[plausible_dates].copy()
        valid_date_rows += len(merged)
        if merged.empty:
            continue

        merged["month"] = parsed_dates.loc[plausible_dates].dt.to_period("M").astype(str)
        grouped = (
            merged.groupby(["month", "Dominant_Topic"], observed=True)
            .size()
            .reset_index(name="absolute_impact")
        )
        totals = merged.groupby(["month"], observed=True).size().reset_index(name="monthly_document_count")
        counts.append(grouped)
        monthly_totals.append(totals)

    if counts:
        result = pd.concat(counts, ignore_index=True)
        result = (
            result.groupby(["month", "Dominant_Topic"], observed=True)["absolute_impact"]
            .sum()
            .reset_index()
        )
        totals = pd.concat(monthly_totals, ignore_index=True)
        totals = totals.groupby("month", observed=True)["monthly_document_count"].sum().reset_index()
        result = result.merge(totals, on="month", how="left")
        result["relative_impact"] = result["absolute_impact"] / result["monthly_document_count"]
        result.insert(0, "stakeholder", stakeholder)
        result = result.rename(columns={"Dominant_Topic": "topic_id"})
        result = result[
            [
                "stakeholder",
                "month",
                "topic_id",
                "absolute_impact",
                "relative_impact",
                "monthly_document_count",
            ]
        ].sort_values(["stakeholder", "month", "topic_id"])
    else:
        result = pd.DataFrame(
            columns=[
                "stakeholder",
                "month",
                "topic_id",
                "absolute_impact",
                "relative_impact",
                "monthly_document_count",
            ]
        )

    stats.update(
        {
            "stakeholder": stakeholder,
            "raw_file": str(raw_path),
            "raw_rows": int(total_raw_rows),
            "rows_matched_to_topic_assignment": int(matched_topic_rows),
            "rows_with_valid_dates_after_topic_match": int(valid_date_rows),
            "rows_with_invalid_dates_after_topic_match": int(invalid_date_rows),
            "rows_with_out_of_range_dates_after_topic_match": int(out_of_range_date_rows),
            "date_filter_min": str(min_date.date()),
            "date_filter_max": str(max_date.date()),
            "matched_topic_rate_vs_raw": matched_topic_rows / total_raw_rows if total_raw_rows else 0,
            "valid_date_rate_vs_matched": valid_date_rows / matched_topic_rows if matched_topic_rows else 0,
            "months": int(result["month"].nunique()) if not result.empty else 0,
            "output_rows": int(len(result)),
        }
    )
    return result, stats


def aggregate_monthly_from_topic_file(
    *,
    stakeholder: str,
    topic_path: Path,
    date_col: str,
    chunksize: int,
    min_date: pd.Timestamp,
    max_date: pd.Timestamp,
) -> tuple[pd.DataFrame, dict]:
    total_rows = 0
    valid_date_rows = 0
    invalid_date_rows = 0
    out_of_range_date_rows = 0
    topic_values: set[int] = set()
    counts: list[pd.DataFrame] = []
    monthly_totals: list[pd.DataFrame] = []

    for chunk in pd.read_csv(
        topic_path,
        usecols=[date_col, "Dominant_Topic"],
        chunksize=chunksize,
        encoding_errors="replace",
        low_memory=False,
        on_bad_lines="warn",
    ):
        total_rows += len(chunk)
        chunk["Dominant_Topic"] = pd.to_numeric(chunk["Dominant_Topic"], errors="coerce")
        parsed_dates = parse_dates(chunk[date_col])
        valid_topic = chunk["Dominant_Topic"].notna()
        invalid_date_rows += int((parsed_dates.isna() & valid_topic).sum())
        plausible_dates = parsed_dates.notna() & parsed_dates.between(min_date, max_date, inclusive="both")
        out_of_range_date_rows += int((parsed_dates.notna() & ~plausible_dates & valid_topic).sum())

        filtered = chunk.loc[valid_topic & plausible_dates, ["Dominant_Topic"]].copy()
        valid_date_rows += len(filtered)
        if filtered.empty:
            continue

        filtered["Dominant_Topic"] = filtered["Dominant_Topic"].astype("int64")
        topic_values.update(filtered["Dominant_Topic"].unique().tolist())
        filtered["month"] = parsed_dates.loc[valid_topic & plausible_dates].dt.to_period("M").astype(str)
        grouped = (
            filtered.groupby(["month", "Dominant_Topic"], observed=True)
            .size()
            .reset_index(name="absolute_impact")
        )
        totals = filtered.groupby(["month"], observed=True).size().reset_index(name="monthly_document_count")
        counts.append(grouped)
        monthly_totals.append(totals)

    if counts:
        result = pd.concat(counts, ignore_index=True)
        result = (
            result.groupby(["month", "Dominant_Topic"], observed=True)["absolute_impact"]
            .sum()
            .reset_index()
        )
        totals = pd.concat(monthly_totals, ignore_index=True)
        totals = totals.groupby("month", observed=True)["monthly_document_count"].sum().reset_index()
        result = result.merge(totals, on="month", how="left")
        result["relative_impact"] = result["absolute_impact"] / result["monthly_document_count"]
        result.insert(0, "stakeholder", stakeholder)
        result = result.rename(columns={"Dominant_Topic": "topic_id"})
        result = result[
            [
                "stakeholder",
                "month",
                "topic_id",
                "absolute_impact",
                "relative_impact",
                "monthly_document_count",
            ]
        ].sort_values(["stakeholder", "month", "topic_id"])
    else:
        result = pd.DataFrame(
            columns=[
                "stakeholder",
                "month",
                "topic_id",
                "absolute_impact",
                "relative_impact",
                "monthly_document_count",
            ]
        )

    stats = {
        "stakeholder": stakeholder,
        "topic_assignment_file": str(topic_path),
        "topic_assignment_rows": int(total_rows),
        "topic_count": int(len(topic_values)),
        "rows_with_valid_dates_after_topic_match": int(valid_date_rows),
        "rows_with_invalid_dates_after_topic_match": int(invalid_date_rows),
        "rows_with_out_of_range_dates_after_topic_match": int(out_of_range_date_rows),
        "date_filter_min": str(min_date.date()),
        "date_filter_max": str(max_date.date()),
        "valid_date_rate_vs_topic_rows": valid_date_rows / total_rows if total_rows else 0,
        "months": int(result["month"].nunique()) if not result.empty else 0,
        "output_rows": int(len(result)),
    }
    return result, stats


def write_wide_outputs(df: pd.DataFrame) -> None:
    for stakeholder, sdf in df.groupby("stakeholder", observed=True):
        wide_abs = sdf.pivot_table(
            index="month",
            columns="topic_id",
            values="absolute_impact",
            aggfunc="sum",
            fill_value=0,
        )
        wide_abs.columns = [f"topic_{int(col)}" for col in wide_abs.columns]
        wide_abs.reset_index().to_csv(OUT_DIR / f"{stakeholder}_monthly_topic_absolute_wide.csv", index=False)

        wide_rel = sdf.pivot_table(
            index="month",
            columns="topic_id",
            values="relative_impact",
            aggfunc="sum",
            fill_value=0,
        )
        wide_rel.columns = [f"topic_{int(col)}" for col in wide_rel.columns]
        wide_rel.reset_index().to_csv(OUT_DIR / f"{stakeholder}_monthly_topic_relative_wide.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunksize", type=int, default=200_000)
    parser.add_argument("--min-date", default="2010-01-01")
    parser.add_argument("--max-date", default="2030-12-31")
    args = parser.parse_args()
    min_date = pd.Timestamp(args.min_date)
    max_date = pd.Timestamp(args.max_date)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    user_df, user_stats = aggregate_monthly_from_topic_file(
        stakeholder="user",
        topic_path=TOPIC_DIR / "User_lda_topics.csv",
        date_col="review_date",
        chunksize=args.chunksize,
        min_date=min_date,
        max_date=max_date,
    )
    developer_df, developer_stats = aggregate_monthly(
        stakeholder="developer",
        raw_path=RAW_DIR / "Developer_posts.csv",
        topic_path=TOPIC_DIR / "Developer_lda_topics.csv",
        id_col="PostID",
        date_col="CreationDate",
        chunksize=args.chunksize,
        min_date=min_date,
        max_date=max_date,
    )

    monthly = pd.concat([user_df, developer_df], ignore_index=True)
    monthly.to_csv(OUT_DIR / "monthly_topic_impact_long.csv", index=False)
    write_wide_outputs(monthly)

    diagnostics = {
        "outputs": {
            "long": str(OUT_DIR / "monthly_topic_impact_long.csv"),
            "user_absolute_wide": str(OUT_DIR / "user_monthly_topic_absolute_wide.csv"),
            "user_relative_wide": str(OUT_DIR / "user_monthly_topic_relative_wide.csv"),
            "developer_absolute_wide": str(OUT_DIR / "developer_monthly_topic_absolute_wide.csv"),
            "developer_relative_wide": str(OUT_DIR / "developer_monthly_topic_relative_wide.csv"),
        },
        "user": user_stats,
        "developer": developer_stats,
    }
    (OUT_DIR / "monthly_topic_impact_diagnostics.json").write_text(
        json.dumps(diagnostics, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    main()
