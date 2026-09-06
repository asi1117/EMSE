# Data Guide

## Overview and data availability

This directory contains the compact public data package accompanying the manuscript. It includes quality-controlled inspection samples, final topic labels, monthly experiment inputs, validated cross-stakeholder mappings, statistical results, and document-topic assignment validation materials. All released analytical data use an inclusive cutoff of **July 31, 2024**, and the common comparison window for the user and developer corpora is **June 2015 through July 2024** (110 months).

The complete analysis-ready corpora and original source exports exceed GitHub's file-size limits and are therefore not included in this repository. The full processed corpora contain **389,473 developer posts** and **913,322 user reviews**. Researchers who require the complete data for verification or non-commercial research may contact the corresponding author using the contact information provided in the accompanying article. Requests should identify the article, the requester's institutional affiliation, and the intended research use. Access is available upon reasonable request and remains subject to applicable platform terms, privacy considerations, and redistribution restrictions.

The 1,000-record samples included here support inspection and auditing; they are not substitutes for the complete analytical corpora.

## Directory contents

### `01_final_processed/`

- `Developer_posts_sample_1000.csv`: 1,000 quality-controlled developer posts.
- `User_reviews_sample_1000.csv`: 1,000 quality-controlled user reviews.

The two samples are stratified over the 41 validated cross-stakeholder topic mappings. The fields `mapping_id` and `within_mapping_sample_index` connect records to the corresponding topic-pair sampling position. This alignment is at the topic-pair level and does not indicate that an individual user review and developer post describe the same event.

### `02_final_topic_assignments/`

- `Developer_lda_topics_sample_1000.csv`: dominant-topic assignments and keywords for the sampled developer posts.
- `User_lda_topics_sample_1000.csv`: dominant-topic assignments and topic-distribution values for the sampled user reviews.

These files contain exactly the same sampled records as `01_final_processed/`. The initial LDA solutions contain 40 developer topics and 50 user topics. Semantically overlapping topics were consolidated into the 37 developer topics and 43 user topics reported in the manuscript.

### `03_topic_keywords_labels/`

- `Developer_topic_merged_labels_final.csv`: the 37 final developer-topic labels, keywords, definitions, and common-window counts.
- `User_topic_merged_labels_final.csv`: the 43 final user-topic labels, keywords, definitions, and common-window counts.

`Rows_Common_Window` records the number of rows assigned to a final topic in the common window. `Valid_Rows_Common_Window` records the observations retained after the date and validity checks used for the monthly analyses.

### `06_experiment_inputs/`

- `monthly_final_topic_impact_common_window.csv`: the primary long-format monthly dataset for both stakeholder groups. It contains absolute impact, relative impact, and monthly document counts.
- `final_topic_inventory_common_window.csv`: the final 37-topic developer inventory and 43-topic user inventory.
- `developer_final_topic_relative_common_window.csv`: developer relative-impact data in wide format.
- `user_final_topic_relative_common_window.csv`: user relative-impact data in wide format.

For a final topic `z` in month `m`, `absolute_impact` is the number of documents assigned to `z` as their dominant topic. `relative_impact` is `absolute_impact` divided by the total number of valid documents for that stakeholder group in month `m`.

### `07_cross_stakeholder_mapping/`

- `topic_mapping_validated.csv`: the complete validated mapping inventory, containing 41 retained user-developer topic pairs and 12 user-salient topics retained for gap discussion only.
- `topic_mapping_validated_matched_only.csv`: the 41 matched topic pairs used in the alignment, salience-gap, lagged-correlation, and paired-sample analyses.

### `08_cross_stakeholder_statistics/`

- `alignment_gap_and_best_lag_validated_mapping.csv`: alignment scores, salience gaps, best lags, and permutation-test results for the 41 validated pairs.
- `lagged_correlation_all_lags_validated_mapping.csv`: Spearman correlations for lags from -12 to +12 months.
- `figure_alignment_gap_distribution_data.csv`: plotting data for the alignment and salience-gap figure.
- `pair_level_maxstat/`: pair-level exact maximum-statistic results for the primary ±12-month analysis and the ±6-month robustness analysis.
- `top_aligned_topic_pairs_validated_mapping.csv`: the most closely aligned pairs.
- `top_developer_salient_topic_pairs_validated_mapping.csv`: pairs with greater developer salience.
- `top_user_salient_topic_pairs_validated_mapping.csv`: pairs with greater user salience.

Positive `best_lag_months` values mean that the developer series leads the user series under the lag convention used in the analysis; negative values mean that the user series leads.

### `09_document_topic_assignment_validation/`

- `documents_blind_review_A.csv`: 240 assignments evaluated by reviewer A.
- `documents_blind_review_B.csv`: the same 240 assignments evaluated independently by reviewer B.
- `documents_disagreements_for_adjudication.csv`: the 14 reviewer disagreements and their final adjudication decisions.

The unique comparison key for this validation is the combination of `stakeholder`, `document_id`, and `assigned_topic_label`.


## Data format and interpretation

- CSV files are encoded as UTF-8 and include a header row.
- Dates and monthly periods use UTC-derived timestamps or `YYYY-MM` notation as indicated by the column name.
- Missing evaluator notes are intentional when no explanatory note was entered.
- Platform-level provenance is not included in this release by design.
- The corpora are not platform-balanced or demographically normalized. Results describe public discussion in the collected sources and should not be interpreted as platform-invariant effects or as representative of all VR application domains.


