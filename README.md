# EMSE-D-26-00378 Replication Package

This repository contains replication materials for:

**Mind the Gap: A Decade-Scale Empirical Study of Multi-Stakeholder Dynamics in VR Ecosystem**

The package supports verification of the revised cross-stakeholder analysis, longitudinal topic-impact analysis, and document-to-topic assignment validation reported in the manuscript.

## What This Package Contains

This GitHub-ready package includes derived data tables, validation samples, statistical outputs, and reproduction scripts. It is designed so reviewers can verify the main revised claims without downloading the full raw corpus.

The full raw and per-document topic-assignment files are large and exceed normal GitHub file limits. They should be hosted with Git LFS or an archival service such as Zenodo/OSF if full end-to-end reruns are required.

## Key Reproducible Claims

The package supports checking the following manuscript claims:

- Common observation window for cross-stakeholder temporal analysis: **June 2015 to July 2024**.
- Final topic inventory in the common window: **43 user topics** and **37 developer topics**.
- Validated cross-stakeholder mapping: **41 user-developer topic pairs**.

## Repository Structure

```text
EMSE_Replication_Package/
  README.md
  REPRODUCE.md
  requirements.txt
  data_manifest.tsv
  .gitignore
  .gitattributes
  data/
    03_topic_keywords_labels/
      topic keyword and label files
    05_samples_and_diagnostics/
      1,000-row public samples for inspection
    06_experiment_inputs/
      monthly topic-impact inputs and final-topic inventory
    07_cross_stakeholder_mapping/
      initial and validated user-developer topic mappings
    08_cross_stakeholder_statistics/
      alignment, gap, lagged-correlation, and FDR outputs
    09_document_topic_assignment_validation/
      coding protocol, validation samples, evaluator files, and kappa output
    README_LARGE_FILES.md

```

## Quick Start

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the paper-result verification script:

```bash
python scripts/reproduce_paper_results.py
```

Expected output includes the validated mapping counts, alignment statistics, and lag-pattern counts. If final evaluator decision files are present, the script also recomputes document-to-topic validation agreement.

## Data Scope

The study analyzes public data from three major consumer VR platforms:

- Meta
- SteamVR
- Viveport

Developer-side discussions come from public developer forums:

- Meta Forum
- SteamVR Forum
- HTC Vive Forum

The corpus is not genre-stratified. Because these consumer VR platforms are dominated by gaming and entertainment applications, the findings should be interpreted as evidence about public consumer VR discourse rather than all VR application domains.

Public developer forums also do not capture internal issue trackers, private product-planning processes, or closed development workflows. Low public discussion volume should therefore not be interpreted as evidence that developers do not address a topic internally.

## Large Files Not Included in the Standard GitHub Package

The following files are needed only for full end-to-end reruns from raw/per-document data and should be stored via Git LFS or an external archive:

- `data/01_public_raw/User_reviews.csv`
- `data/01_public_raw/Developer_posts.csv`
- `data/02_final_topic_assignments/User_lda_topics.csv`
- `data/02_final_topic_assignments/Developer_lda_topics.csv`

See `data/README_LARGE_FILES.md` for details.



## Citation

If this replication package is used, please cite the associated manuscript:

Lu et al. *Mind the Gap: A Decade-Scale Empirical Study of Multi-Stakeholder Dynamics in VR Ecosystem*. EMSE-D-26-00378.
