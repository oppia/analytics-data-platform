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
-- Purpose: Performance-optimized weekly lesson completion rollup.
-- Note: Column testing and metadata descriptions are defined in _curriculum.yml.

WITH lesson_progress AS (
    SELECT
        user_id,
        lesson_id,
        progress_percent,
        updated_at,
        DATE(updated_at) AS updated_date
    FROM {{ ref('stg_web_analytics__events') }}
),

final_aggregations AS (
    SELECT
        user_id,
        lesson_id,
        progress_percent,
        updated_at,
        updated_date
    FROM lesson_progress
)

SELECT
    user_id,
    lesson_id,
    progress_percent,
    updated_at,
    updated_date
FROM final_aggregations