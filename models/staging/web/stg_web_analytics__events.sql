-- Project: oppia-web-analytics
-- Owner: analytics-team
-- Purpose: Standardized staging layer capturing core web log interactions.
-- Note: Detailed column descriptions and data quality assertions are managed inside the corresponding schema.yml file.

WITH source_data AS (
    -- events_* wildcard scans all daily shards; _TABLE_SUFFIX exposes each shard's date suffix
    SELECT * FROM {{ source('raw_web_server', 'events_*') }}
    WHERE _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))
        AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
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
        -- GA4 stores custom event attributes as key/value pairs rather than fixed columns
        (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location' LIMIT 1) AS page_location,
        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id' LIMIT 1) AS ga_session_id
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
    ga_session_id
FROM final_events
