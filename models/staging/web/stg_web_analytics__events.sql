-- Project: oppia-web-analytics
-- Owner: analytics-team
-- Purpose: Standardized staging layer capturing core web log interactions.
-- Note: Detailed column descriptions and data quality assertions are managed inside the corresponding schema.yml file.

WITH source_data AS (
    SELECT * FROM {{ source('raw_web_server', 'web_events_log') }}
),

final_events AS (
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
FROM final_events
