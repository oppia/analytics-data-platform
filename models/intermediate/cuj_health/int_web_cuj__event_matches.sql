-- Project: CUJ Health Ratings
-- Owner: Product Analytics
-- Purpose: Match staged Web GA4 events to governed CUJ event-mapping rules.
-- PoC scope: LO.6 - Play through all the general question types.

WITH event_bridge AS (
    SELECT
        event_mapping_id,
        cuj_id,
        cuj_step_id,
        platform,
        event_name,
        NULLIF(CAST(required_parameter_key AS STRING), '') AS required_parameter_key,
        NULLIF(CAST(required_parameter_value AS STRING), '') AS required_parameter_value,
        mapping_status,
        is_required_for_rating,
        source_reference
    FROM {{ ref('seed_cuj_event_bridge') }}
    WHERE cuj_id = 'web_external_general_question_types'
      AND platform = 'web'
),

candidate_events AS (
    SELECT *
    FROM {{ ref('stg_web_analytics__events') }}
    WHERE event_name IN (
        SELECT DISTINCT event_name
        FROM event_bridge
    )
),

matched_events AS (
    SELECT
        {{ generate_surrogate_key([
            'e.user_pseudo_id',
            'e.event_timestamp',
            'e.event_name',
            'b.event_mapping_id',
            'e.ga_session_id'
        ]) }} AS event_match_id,

        b.event_mapping_id,
        b.cuj_id,
        b.cuj_step_id,
        b.platform,
        b.mapping_status,
        b.is_required_for_rating,

        e.user_id,
        e.user_pseudo_id,
        e.ga_session_id,
        e.event_name,
        e.event_date,
        e.event_timestamp,

        e.exploration_id,
        e.card_number,
        e.answer_is_correct,
        e.login_status,
        e.page_location,
        e.page_title,

        b.required_parameter_key AS matched_parameter_key,

        CASE b.required_parameter_key
            WHEN 'card_number' THEN CAST(e.card_number AS STRING)
            WHEN 'answer_is_correct' THEN e.answer_is_correct
            ELSE NULL
        END AS matched_parameter_value,

        b.source_reference

    FROM candidate_events AS e
    INNER JOIN event_bridge AS b
        ON e.event_name = b.event_name

    WHERE
        b.required_parameter_key IS NULL

        OR (
            b.required_parameter_key = 'card_number'
            AND e.card_number IS NOT NULL
            AND (
                b.required_parameter_value IS NULL
                OR CAST(e.card_number AS STRING) = b.required_parameter_value
            )
        )

        OR (
            b.required_parameter_key = 'answer_is_correct'
            AND e.answer_is_correct IS NOT NULL
            AND (
                b.required_parameter_value IS NULL
                OR e.answer_is_correct = b.required_parameter_value
            )
        )
)

SELECT
    event_match_id,
    event_mapping_id,
    cuj_id,
    cuj_step_id,
    platform,
    mapping_status,
    is_required_for_rating,
    user_id,
    user_pseudo_id,
    ga_session_id,
    event_name,
    event_date,
    event_timestamp,
    exploration_id,
    card_number,
    answer_is_correct,
    login_status,
    page_location,
    page_title,
    matched_parameter_key,
    matched_parameter_value,
    source_reference
FROM matched_events
