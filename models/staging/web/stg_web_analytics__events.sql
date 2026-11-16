-- Project: oppia-web-analytics
-- Owner: analytics-team
-- Purpose: Standardized staging layer capturing core web log interactions.
-- Note: Detailed column descriptions and data quality assertions are managed inside the corresponding schema.yml file.

WITH source_data AS (
    -- PoC baseline: last 30 completed days, excluding the current day.
    SELECT *
    FROM {{ source('raw_web_server', 'events_*') }}
    WHERE _TABLE_SUFFIX BETWEEN
        FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY))
        AND FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))
),

final_events AS (
    SELECT
        user_id,
        user_pseudo_id,
        event_name,
        event_date,
        TIMESTAMP_MICROS(event_timestamp) AS event_timestamp,
        device.category AS device_category,
        device.operating_system AS operating_system,
        geo.country AS country,
        traffic_source.source AS traffic_source,
        traffic_source.medium AS traffic_medium,

        -- GA4 event parameters required by the first CUJ Health PoC.
        (SELECT value.string_value
         FROM UNNEST(event_params)
         WHERE key = 'page_location'
         LIMIT 1) AS page_location,

        (SELECT value.string_value
         FROM UNNEST(event_params)
         WHERE key = 'page_title'
         LIMIT 1) AS page_title,

        (SELECT value.int_value
         FROM UNNEST(event_params)
         WHERE key = 'ga_session_id'
         LIMIT 1) AS ga_session_id,

        (SELECT value.string_value
         FROM UNNEST(event_params)
         WHERE key = 'exploration_id'
         LIMIT 1) AS exploration_id,

        (SELECT value.int_value
         FROM UNNEST(event_params)
         WHERE key = 'card_number'
         LIMIT 1) AS card_number,

        (SELECT value.string_value
         FROM UNNEST(event_params)
         WHERE key = 'answer_is_correct'
         LIMIT 1) AS answer_is_correct,

        (SELECT value.string_value
         FROM UNNEST(event_params)
         WHERE key = 'login_status'
         LIMIT 1) AS login_status

    FROM source_data
)

SELECT
    user_id,
    user_pseudo_id,
    event_name,
    event_date,
    event_timestamp,
    device_category,
    operating_system,
    country,
    traffic_source,
    traffic_medium,
    page_location,
    page_title,
    ga_session_id,
    exploration_id,
    card_number,
    answer_is_correct,
    login_status
FROM final_events
