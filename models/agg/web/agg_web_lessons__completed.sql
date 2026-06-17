{{ config(
    materialized='table',
    partition_by={
      "field": "updated_date",
      "data_type": "date",
      "granularity": "day"
    },
    cluster_by=["user_id", "lesson_id"]
) }}

-- Project: oppia-web-analytics
-- Owner: analytics-team
-- Purpose: Performance-optimized summary rollup tracking completed web lessons.
-- Note: Column testing and metadata descriptions are defined in models/schema.yml.

WITH lesson_progress AS (
    SELECT
        user_id,
        lesson_id,
        progress_percent,
        updated_at,
        -- Creating a safe date field for BigQuery partitioning
        DATE(updated_at) AS updated_date
    FROM {{ ref('stg_web_events') }}
),

final_aggregations AS (
    SELECT
        user_id,
        lesson_id,
        progress_percent,
        updated_at,
        updated_date
    FROM lesson_progress
    -- In a real production scenario, you would add your aggregation filters here, e.g.:
    -- WHERE progress_percent = 100
)

SELECT
    user_id,
    lesson_id,
    progress_percent,
    updated_at,
    updated_date
FROM final_aggregations
