import csv
import random
from collections import defaultdict
from pathlib import Path


BASE = Path(r"D:\EMSE\Round3")
DATASET = BASE / "Dataset"
OUT_DIR = DATASET / "09_document_topic_assignment_validation"

USER_ASSIGNMENTS = DATASET / "02_final_topic_assignments" / "User_lda_topics.csv"
DEV_ASSIGNMENTS = DATASET / "02_final_topic_assignments" / "Developer_lda_topics.csv"
INVENTORY = DATASET / "06_experiment_inputs" / "final_topic_inventory_common_window_2015-06_2024-07.csv"
USER_RAW_LABELS = DATASET / "03_topic_keywords_labels" / "User_topic_merged_labels_final.tsv"
DEV_RAW_LABELS = Path(r"D:\EMSE\Data\JSS\Developer\merged_output.csv")

SAMPLES_PER_FINAL_TOPIC = 3
RANDOM_SEED = 20260808
TEXT_LIMIT = 1400


USER_FINAL_TOPIC_TO_RAW_TOPICS = {
    "Adventure Games": [0],
    "Audio Interactions": [7],
    "Comfort Issues": [2, 29],
    "Customization": [3, 18],
    "Female Character": [4, 11],
    "Game Content": [5, 12],
    "Game Graphics": [6, 16],
    "Game Interface": [7, 13, 41],
    "Game Mechanics": [8],
    "Game Story": [9],
    "Game Strategy": [10],
    "Game Style": [11],
    "Gameplay Complexity": [12],
    "Golfing Game": [13, 17],
    "Hardware Support": [14],
    "Horror Game": [15],
    "Input Methods": [16],
    "Installation": [17],
    "Interaction Methods": [18],
    "Kids and Students": [19],
    "Language": [20],
    "LGBTQ": [21],
    "Light Design": [22],
    "Linux OS": [23],
    "Mac OS": [24],
    "Motion Design": [25],
    "Multiplayer": [26],
    "Network connect": [27],
    "Performance Issues": [28],
    "Physical Reactions": [29],
    "Play Scale": [30],
    "Pricing": [31],
    "Privacy & Security": [32],
    "Rhythm Games": [33],
    "Scene Design": [34],
    "Setup": [35],
    "Sound Design": [36],
    "Sports Games": [37],
    "Target Tracking": [38],
    "Technical Issues": [39],
    "Troubleshooting": [40],
    "UI Design": [41],
    "VR Elements": [42],
}


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
                    "final_topic_label": clean_text(row["topic_label"]),
                }
            )
    return inventory


def load_raw_labels(path, delimiter=",", label_field="Merged_GPT_Label", fallback_field="GPT_Label"):
    labels = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            topic = str(row.get("Topic", "")).strip()
            label = clean_text(row.get(label_field, "")) or clean_text(row.get(fallback_field, ""))
            labels[topic] = {
                "raw_label": label or f"Topic {topic}",
                "keywords": clean_text(row.get("Keywords", "")),
            }
    return labels


def load_user_raw_labels():
    return load_raw_labels(USER_RAW_LABELS, delimiter="\t", label_field="Merged_GPT_Label", fallback_field="GPT_Label")


def load_dev_raw_labels():
    return load_raw_labels(DEV_RAW_LABELS, delimiter=",", label_field="Merged_GPT_Label2", fallback_field="GPT_Label2")


def collect_rows_by_raw_topic(path, text_field):
    rows_by_topic = defaultdict(list)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            topic = str(row.get("Dominant_Topic", "")).strip()
            if not topic or not clean_text(row.get(text_field, "")):
                continue
            rows_by_topic[topic].append(row)
    return rows_by_topic


def weighted_sample(rows, n, rng):
    if len(rows) <= n:
        return list(rows)
    return rng.sample(rows, n)


def create_user_records(inventory, raw_labels):
    rng = random.Random(RANDOM_SEED + 11)
    rows_by_topic = collect_rows_by_raw_topic(USER_ASSIGNMENTS, "review")
    records = []
    for item in inventory["user"]:
        final_label = item["final_topic_label"]
        raw_topics = USER_FINAL_TOPIC_TO_RAW_TOPICS.get(final_label, [int(item["final_topic_id"])])
        candidates = []
        raw_keyword_parts = []
        for raw_topic in raw_topics:
            topic_key = str(raw_topic)
            candidates.extend(rows_by_topic.get(topic_key, []))
            if topic_key in raw_labels:
                raw_keyword_parts.append(raw_labels[topic_key]["keywords"])
        for row in weighted_sample(candidates, SAMPLES_PER_FINAL_TOPIC, rng):
            text, truncated = excerpt(row.get("review", ""))
            raw_topic = str(row.get("Dominant_Topic", "")).strip()
            confidence = row.get(f"Topic_{raw_topic}_Dist", "")
            records.append(
                {
                    "validation_id": "",
                    "stakeholder": "user",
                    "document_id": clean_text(row.get("Review_ID", "")),
                    "raw_topic_id": raw_topic,
                    "assigned_topic_label": final_label,
                    "topic_keywords": "; ".join(k for k in raw_keyword_parts if k),
                    "assignment_confidence": confidence,
                    "document_text_excerpt": text,
                    "text_was_truncated": truncated,
                    "evaluator_decision": "",
                    "evaluator_note": "",
                }
            )
    return records


def create_developer_records(inventory, raw_labels):
    rng = random.Random(RANDOM_SEED + 22)
    rows_by_topic = collect_rows_by_raw_topic(DEV_ASSIGNMENTS, "Text")
    records = []
    for item in inventory["developer"]:
        raw_topic = item["final_topic_id"]
        candidates = rows_by_topic.get(raw_topic, [])
        meta = raw_labels.get(raw_topic, {"keywords": ""})
        for row in weighted_sample(candidates, SAMPLES_PER_FINAL_TOPIC, rng):
            text, truncated = excerpt(row.get("Text", ""))
            records.append(
                {
                    "validation_id": "",
                    "stakeholder": "developer",
                    "document_id": clean_text(row.get("PostID", "")),
                    "raw_topic_id": raw_topic,
                    "assigned_topic_label": item["final_topic_label"],
                    "topic_keywords": meta["keywords"],
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
    records = []
    records.extend(create_user_records(inventory, load_user_raw_labels()))
    records.extend(create_developer_records(inventory, load_dev_raw_labels()))

    for i, row in enumerate(records, start=1):
        row["validation_id"] = f"FDTA{i:04d}"

    paths = [
        OUT_DIR / "final_topic_assignment_validation_sample_master.csv",
        OUT_DIR / "final_topic_assignment_validation_evaluator1.csv",
        OUT_DIR / "final_topic_assignment_validation_evaluator2.csv",
    ]
    for path in paths:
        write_csv(path, records)

    summary = OUT_DIR / "final_topic_assignment_validation_sampling_summary.txt"
    counts = defaultdict(int)
    for row in records:
        counts[(row["stakeholder"], row["assigned_topic_label"])] += 1
    with summary.open("w", encoding="utf-8") as f:
        f.write(f"random_seed={RANDOM_SEED}\n")
        f.write(f"samples_per_final_topic={SAMPLES_PER_FINAL_TOPIC}\n")
        f.write(f"total_samples={len(records)}\n")
        f.write(f"user_samples={sum(1 for r in records if r['stakeholder']=='user')}\n")
        f.write(f"developer_samples={sum(1 for r in records if r['stakeholder']=='developer')}\n")
        f.write("valid_decisions=correct,unclear,incorrect\n")
        f.write("coding_instruction=Judge whether the document text is semantically consistent with the assigned final topic label and keywords.\n")
        f.write("\nper_final_topic_samples:\n")
        for key in sorted(counts):
            f.write(f"{key[0]},{key[1]}={counts[key]}\n")

    for path in paths:
        print(path)
    print(summary)


if __name__ == "__main__":
    main()
