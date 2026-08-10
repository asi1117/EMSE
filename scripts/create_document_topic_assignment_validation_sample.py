import csv
import random
from collections import defaultdict
from pathlib import Path


BASE = Path(r"D:\EMSE\Round3")
DATASET = BASE / "Dataset"
OUT_DIR = DATASET / "09_document_topic_assignment_validation"

USER_ASSIGNMENTS = DATASET / "02_final_topic_assignments" / "User_lda_topics.csv"
DEV_ASSIGNMENTS = DATASET / "02_final_topic_assignments" / "Developer_lda_topics.csv"
USER_LABELS = DATASET / "03_topic_keywords_labels" / "User_topic_merged_labels_final.tsv"
DEV_LABELS = Path(r"D:\EMSE\Data\JSS\Developer\merged_output.csv")

SAMPLES_PER_TOPIC = 5
RANDOM_SEED = 20260808
TEXT_LIMIT = 1400


def clean_text(value):
    value = (value or "").replace("\r", " ").replace("\n", " ")
    value = " ".join(value.split())
    return value


def excerpt(value):
    text = clean_text(value)
    return text[:TEXT_LIMIT], "yes" if len(text) > TEXT_LIMIT else "no"


def load_user_labels(path):
    labels = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            topic = str(row.get("Topic", "")).strip()
            merged = clean_text(row.get("Merged_GPT_Label", ""))
            label = merged or clean_text(row.get("GPT_Label", "")) or f"Topic {topic}"
            labels[topic] = {
                "label": label,
                "keywords": clean_text(row.get("Keywords", "")),
            }
    return labels


def load_developer_labels(path):
    labels = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            topic = str(row.get("Topic", "")).strip()
            label = clean_text(row.get("Merged_GPT_Label2", "")) or clean_text(row.get("GPT_Label2", ""))
            label = label or clean_text(row.get("GPT_Label", "")) or f"Topic {topic}"
            labels[topic] = {
                "label": label,
                "keywords": clean_text(row.get("Keywords", "")),
            }
    return labels


def reservoir_sample_by_topic(path, stakeholder, text_field, id_field, labels):
    rng = random.Random(RANDOM_SEED + (1 if stakeholder == "user" else 2))
    samples = defaultdict(list)
    counts = defaultdict(int)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            topic = str(row.get("Dominant_Topic", "")).strip()
            if topic == "":
                continue
            text = clean_text(row.get(text_field, ""))
            if not text:
                continue
            counts[topic] += 1
            slot = samples[topic]
            if len(slot) < SAMPLES_PER_TOPIC:
                slot.append(row)
            else:
                j = rng.randint(1, counts[topic])
                if j <= SAMPLES_PER_TOPIC:
                    slot[j - 1] = row

    records = []
    for topic in sorted(samples, key=lambda x: int(float(x)) if x.replace(".", "", 1).isdigit() else x):
        meta = labels.get(topic, {"label": f"Topic {topic}", "keywords": ""})
        for local_idx, row in enumerate(samples[topic], start=1):
            text_value, was_truncated = excerpt(row.get(text_field, ""))
            doc_id = clean_text(row.get(id_field, "")) or f"{stakeholder}_{topic}_{local_idx}"
            confidence = ""
            dist_col = f"Topic_{topic}_Dist"
            if dist_col in row:
                confidence = row.get(dist_col, "")
            records.append(
                {
                    "validation_id": "",
                    "stakeholder": stakeholder,
                    "document_id": doc_id,
                    "raw_topic_id": topic,
                    "assigned_topic_label": meta["label"],
                    "topic_keywords": meta["keywords"],
                    "assignment_confidence": confidence,
                    "document_text_excerpt": text_value,
                    "text_was_truncated": was_truncated,
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
        for row in rows:
            writer.writerow(row)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    user_labels = load_user_labels(USER_LABELS)
    dev_labels = load_developer_labels(DEV_LABELS)

    rows = []
    rows.extend(reservoir_sample_by_topic(USER_ASSIGNMENTS, "user", "review", "Review_ID", user_labels))
    rows.extend(reservoir_sample_by_topic(DEV_ASSIGNMENTS, "developer", "Text", "PostID", dev_labels))

    for idx, row in enumerate(rows, start=1):
        row["validation_id"] = f"DTA{idx:04d}"

    master = OUT_DIR / "document_topic_assignment_validation_sample_master.csv"
    eval1 = OUT_DIR / "document_topic_assignment_validation_evaluator1.csv"
    eval2 = OUT_DIR / "document_topic_assignment_validation_evaluator2.csv"
    write_csv(master, rows)
    write_csv(eval1, rows)
    write_csv(eval2, rows)

    summary = OUT_DIR / "document_topic_assignment_validation_sampling_summary.txt"
    topic_counts = defaultdict(int)
    for row in rows:
        topic_counts[(row["stakeholder"], row["raw_topic_id"])] += 1
    with summary.open("w", encoding="utf-8") as f:
        f.write(f"random_seed={RANDOM_SEED}\n")
        f.write(f"samples_per_topic={SAMPLES_PER_TOPIC}\n")
        f.write(f"total_samples={len(rows)}\n")
        f.write(f"user_samples={sum(1 for r in rows if r['stakeholder']=='user')}\n")
        f.write(f"developer_samples={sum(1 for r in rows if r['stakeholder']=='developer')}\n")
        f.write("valid_decisions=correct,unclear,incorrect\n")
        f.write("coding_instruction=Judge whether the document text is semantically consistent with the assigned topic label and keywords.\n")
        f.write("\nper_topic_samples:\n")
        for key in sorted(topic_counts):
            f.write(f"{key[0]},topic_{key[1]}={topic_counts[key]}\n")

    print(master)
    print(eval1)
    print(eval2)
    print(summary)


if __name__ == "__main__":
    main()
