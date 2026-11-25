-- Project: oppia-web-analytics
-- Owner: analytics-team
-- Purpose: Standardized staging layer capturing core web log interactions.
-- Note: Detailed column descriptions and data quality assertions are managed inside the corresponding schema.yml file.

{{ config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    on_schema_change='sync_all_columns',
    partition_by={
        "field": "event_date",
        "data_type": "date",
        "granularity": "day"
    },
    cluster_by=["event_name", "user_pseudo_id"]
) }}

WITH source_data AS (
    -- events_* wildcard scans daily GA4 shards; _TABLE_SUFFIX exposes each shard's YYYYMMDD date.
    -- Incremental runs reprocess the last 10 days (7-day weekly cadence + 3-day GA4 late-export buffer)
    -- and overwrite only those daily partitions so runs stay strictly idempotent.
    -- Full refreshes scan 90 days in prod (override via --vars '{backfill_days: N}') and 7 days in dev.
    SELECT * FROM {{ source('raw_web_server', 'events_*') }}
    WHERE
        {% if is_incremental() %}
            _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 10 DAY))
            AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
        {% elif target.name == 'prod' %}
            _TABLE_SUFFIX BETWEEN FORMAT_DATE(
                '%Y%m%d',
                DATE_SUB(CURRENT_DATE(), INTERVAL {{ var('backfill_days', 90) }} DAY)
            )
            AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
        {% else %}
            _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY))
            AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
        {% endif %}
),

final_events AS (
    SELECT
        user_id,
        user_pseudo_id,
        event_name,
        PARSE_DATE('%Y%m%d', event_date) AS event_date,
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
