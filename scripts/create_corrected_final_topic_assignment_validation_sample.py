import csv
import sys
import random
from collections import defaultdict
from pathlib import Path


BASE = Path(r"D:\EMSE\Round3")
DATASET = BASE / "Dataset"
OUT_DIR = DATASET / "09_document_topic_assignment_validation"

USER_FINAL_DIR = Path(r"D:\EMSE\Data\JSS\User\ReTopic\Reviews\Final")
DEV_FINAL_DIR = Path(r"D:\EMSE\Data\JSS\Developer\Developer_lda_topics")
INVENTORY = DATASET / "06_experiment_inputs" / "final_topic_inventory_common_window_2015-06_2024-07.csv"

SAMPLES_PER_FINAL_TOPIC = 3
RANDOM_SEED = 20260809
TEXT_LIMIT = 1400

csv.field_size_limit(min(sys.maxsize, 2_147_483_647))


def clean_text(value):
    value = (value or "").replace("\r", " ").replace("\n", " ")
    return " ".join(value.split())


def excerpt(value):
    text = clean_text(value)
    return text[:TEXT_LIMIT], "yes" if len(text) > TEXT_LIMIT else "no"


def load_inventory():
    inventory = {"user": [], "developer": []}
    with INVENTORY.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stakeholder = row["stakeholder"].strip()
            inventory[stakeholder].append(
                {
                    "final_topic_id": row["topic_id"].strip(),
                    "final_topic_label": clean_text(row["topic_label"]).strip(),
                }
            )
    return inventory


def reservoir_sample(path, text_field, n, rng):
    sample = []
    count = 0
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not clean_text(row.get(text_field, "")):
                continue
            count += 1
            if len(sample) < n:
                sample.append(row)
            else:
                j = rng.randint(1, count)
                if j <= n:
                    sample[j - 1] = row
    return sample


def user_records(inventory):
    rng = random.Random(RANDOM_SEED + 1)
    records = []
    for item in inventory["user"]:
        label = item["final_topic_label"]
        path = USER_FINAL_DIR / f"{label}.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        for row in reservoir_sample(path, "review", SAMPLES_PER_FINAL_TOPIC, rng):
            text, truncated = excerpt(row.get("review", ""))
            raw_topic = clean_text(row.get("Dominant_Topic", ""))
            records.append(
                {
                    "validation_id": "",
                    "stakeholder": "user",
                    "document_id": clean_text(row.get("Review_ID", "")),
                    "source_final_topic_file": path.name,
                    "raw_topic_id": raw_topic,
                    "assigned_topic_label": label,
                    "topic_keywords": "",
                    "assignment_confidence": row.get(f"Topic_{raw_topic}_Dist", ""),
                    "document_text_excerpt": text,
                    "text_was_truncated": truncated,
                    "evaluator_decision": "",
                    "evaluator_note": "",
                }
            )
    return records


def developer_records(inventory):
    rng = random.Random(RANDOM_SEED + 2)
    records = []
    for item in inventory["developer"]:
        topic_id = item["final_topic_id"]
        path = DEV_FINAL_DIR / f"topic_{topic_id}.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        for row in reservoir_sample(path, "Text", SAMPLES_PER_FINAL_TOPIC, rng):
            text, truncated = excerpt(row.get("Text", ""))
            records.append(
                {
                    "validation_id": "",
                    "stakeholder": "developer",
                    "document_id": clean_text(row.get("PostID", "")),
                    "source_final_topic_file": path.name,
                    "raw_topic_id": clean_text(row.get("Dominant_Topic", topic_id)),
                    "assigned_topic_label": item["final_topic_label"],
                    "topic_keywords": clean_text(row.get("Top_Keywords", "")),
                    "assignment_confidence": "",
                    "document_text_excerpt": text,
                    "text_was_truncated": truncated,
                    "evaluator_decision": "",
                    "evaluator_note": "",
                }
            )
    return records


def write_csv(path, rows):
    fieldnames = [
        "validation_id",
        "stakeholder",
        "document_id",
        "source_final_topic_file",
        "raw_topic_id",
        "assigned_topic_label",
        "topic_keywords",
        "assignment_confidence",
        "document_text_excerpt",
        "text_was_truncated",
        "evaluator_decision",
        "evaluator_note",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    inventory = load_inventory()
    records = user_records(inventory) + developer_records(inventory)
    for i, row in enumerate(records, start=1):
        row["validation_id"] = f"CFDTA{i:04d}"

    outputs = [
        OUT_DIR / "corrected_final_topic_assignment_validation_sample_master.csv",
        OUT_DIR / "corrected_final_topic_assignment_validation_evaluator1.csv",
        OUT_DIR / "corrected_final_topic_assignment_validation_evaluator2.csv",
    ]
    for output in outputs:
        write_csv(output, records)

    counts = defaultdict(int)
    for row in records:
        counts[(row["stakeholder"], row["assigned_topic_label"])] += 1
    summary = OUT_DIR / "corrected_final_topic_assignment_validation_sampling_summary.txt"
    with summary.open("w", encoding="utf-8") as f:
        f.write(f"random_seed={RANDOM_SEED}\n")
        f.write(f"samples_per_final_topic={SAMPLES_PER_FINAL_TOPIC}\n")
        f.write(f"total_samples={len(records)}\n")
        f.write(f"user_samples={sum(1 for r in records if r['stakeholder']=='user')}\n")
        f.write(f"developer_samples={sum(1 for r in records if r['stakeholder']=='developer')}\n")
        f.write("valid_decisions=correct,unclear,incorrect\n")
        f.write("sampling_source=final topic-specific files, not raw topic-id assumptions\n")
        f.write("\nper_final_topic_samples:\n")
        for key in sorted(counts):
            f.write(f"{key[0]},{key[1]}={counts[key]}\n")

    for output in outputs:
        print(output)
    print(summary)


if __name__ == "__main__":
    main()
