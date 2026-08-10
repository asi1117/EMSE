# Large Files

The standard GitHub package intentionally excludes full raw and per-document topic-assignment files because several exceed GitHub's normal 100 MB single-file limit.

For a full end-to-end rerun, provide the following files through Git LFS, Zenodo, OSF, or another archival service:

```text
data/01_public_raw/User_reviews.csv
data/01_public_raw/Developer_posts.csv
data/02_final_topic_assignments/User_lda_topics.csv
data/02_final_topic_assignments/Developer_lda_topics.csv
```

Recommended placement after download:

```text
EMSE_Replication_Package/
  data/
    01_public_raw/
      User_reviews.csv
      Developer_posts.csv
    02_final_topic_assignments/
      User_lda_topics.csv
      Developer_lda_topics.csv
```

The included derived tables are sufficient to verify the revised cross-stakeholder claims reported in the manuscript.

