# Oppia Transformation Layer (dbt Models)

Welcome to the data modeling layer for the Oppia Product Analytics pipeline. This directory contains all transformation logic translating granular web and Android database event logs into analysis-ready reporting datasets.

## Pipeline Architecture & Multi-Project Routing
Our analytics infrastructure spans multiple Google Cloud Projects (GCP) to isolate development from live production dashboards. dbt handles the routing across these environments automatically based on your execution command target.

* **Test Environment (`oppia-analytics-test`)**: Used for local analyst development and automated Pull Request checks. Reads raw logs from the test web/Android servers and outputs to `test_stg`, `test_dim`, `test_fct`, and `test_agg`.
* **Production Environment (`oppia-analytics-prod`)**: Houses live dashboards. Reads raw logs from production web/Android servers and outputs to `prod_stg`, `prod_dim`, `prod_fct`, and `prod_agg`.

---

## 🛠️ Analyst & Developer Workflow

To ensure pipeline stability and prevent breaking production data structures, all contributors must strictly follow this development lifecycle.

### Phase 1: Local Feature Development
When tasked with writing a new SQL query or editing an existing model, do not modify production files directly.

1. **Create a Feature Branch:** Pull the latest changes from `develop` and open a local feature branch:
```bash
    git checkout develop
    git pull origin develop
    git checkout -b feature/your-feature-name
    ```
2. **Write Pure SQL according to the Platform Skeleton:** Create your model inside the appropriate directory (e.g., `/models/stg/web/`). Write your query utilizing proper CTE naming conventions, ensuring `SELECT *` is avoided in final projection blocks.

    Every dbt model script must follow this structure:
```sql
    -- Project: oppia-web-analytics or oppia-android-analytics
    -- Owner: analytics-team
    -- Purpose: Brief single-sentence explanation of what this specific asset evaluates.
    -- Note: Detailed column descriptions and data quality assertions are managed inside the corresponding schema.yml file.

    WITH source_data AS (
        SELECT * FROM {{ ref('stg_web_events') }}
    ),

    lesson_progress AS (
        SELECT
            user_id,
            lesson_id,
            progress_percent,
            updated_at
        FROM source_data
    )

    SELECT
        user_id,
        lesson_id,
        progress_percent,
        updated_at
    FROM lesson_progress
    ```
    *Never hardcode absolute dataset paths; always use the dependency tracking reference macro `{{ ref() }}` or `{{ source() }}`.*

3. **Run Locally in Sandbox:** Execute your code using the dev target. dbt will safely direct your models to build inside your own personal sandbox dataset within the test project:
```bash
    dbt run --target dev
    ```
4. **Add Schema Definitions:** Document your model and columns inside the corresponding `schema.yml` file. Define data quality tests (such as `not_null` or `unique`) on critical keys.

### Phase 2: Pull Request & Automated Code Validation (CI)
Once your local runs compile successfully and your data quality looks accurate, it is time to move your code toward production.

1. **Commit and Push:** Push your feature branch to GitHub:
```bash
    git add .
    git commit -m "feat: added web lesson completed aggregation"
    git push origin feature/your-feature-name
    ```
2. **Open a Pull Request (PR):** Open a PR targeting the `develop` branch.
3. **Automated Quality Gates:** Opening the PR automatically kicks off a GitHub Actions CI pipeline. This pipeline logs into `oppia-analytics-test`, checks your SQL syntax, verifies model relationships, and builds the lineage tree.
    * *If the pipeline fails, the PR will block merging until you fix the compilation or syntax errors.*
4. **Peer Review:** At least one team member must review and approve your PR before it can be merged into `develop`.

### Phase 3: Deployment to Production
Once approved and merged into `develop`, the automation pipeline takes over.

* **Weekly Automated Production Run:** Every Sunday at midnight UTC, a production GitHub Action wakes up, targets the `prod` configuration, and executes the updated codebase against live production data inside `oppia-analytics-prod`.
* **One-off Production Runs:** If an urgent run is required between weekly cycles, an analytics team lead can manually trigger a production run via the **Actions** tab in the GitHub UI using the `workflow_dispatch` option.

---

## Data Modeling Tiers & Pipeline Execution Guarantees
All scripts across these tiers must be **strictly idempotent**. Running a pipeline or individual script multiple times must produce the exact same table state without duplicating metrics, multiplying records, or generating orphaned rows.

1. **Staging (`stg/`)**: Source-aligned data cleaning and standardized data-type casting mapping 1:1 with source nodes.
2. **Dimensions (`dim/`)**: Descriptive master lookup models tracking slow-moving contextual profile properties (e.g., users, lessons).
3. **Facts (`fct/`)**: Immutable chronological event streams capturing core atomic user actions.
4. **Aggregations (`agg/`)**: High-performance, performance-optimized summary metric rollups designed directly for visualization layer connections.

---

## ⚙️ Performance Optimization (Partitioning & Clustering)

To optimize query performance and minimize Google Cloud BigQuery analysis costs, all high-volume tables (especially within the `fct/` and `agg/` layers) must utilize dbt configuration blocks for performance tuning:

* **Partitioning:** Every transaction or event stream must be partitioned by a date or timestamp column (e.g., `event_at` or `created_at`). This isolates queries to specific time ranges instead of scanning the entire table history.
* **Clustering:** Tables must be clustered by high-cardinality columns that are frequently used in `WHERE` filters or `JOIN` clauses (e.g., `platform`, `user_id`, `lesson_id`).

### How to Implement This in a Model File
Analysts must add a dbt configuration block to the very top of their SQL file like this:

```sql
{{ config(
    materialized='table',
    partition_by={
      "field": "event_date",
      "data_type": "date",
      "granularity": "day"
    },
    cluster_by=["platform", "lesson_id"]
) }}

WITH raw_data AS (
    SELECT * FROM {{ ref('stg_web_events') }}
),
...
