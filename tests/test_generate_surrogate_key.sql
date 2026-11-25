-- Singular dbt test for the generate_surrogate_key macro.
-- Runs in BigQuery with zero table scans; fails if any assertion row is returned.

WITH sample_inputs AS (
    SELECT
        'string_and_int_cast' AS case_name,
        'user_1' AS str_col,
        42 AS int_col,
        TO_HEX(MD5('user_1-42')) AS expected_key
    UNION ALL
    SELECT
        'trailing_null_sentinel' AS case_name,
        'user_1' AS str_col,
        CAST(NULL AS INT64) AS int_col,
        TO_HEX(MD5('user_1-_null_')) AS expected_key
    UNION ALL
    SELECT
        'leading_null_sentinel' AS case_name,
        CAST(NULL AS STRING) AS str_col,
        42 AS int_col,
        TO_HEX(MD5('_null_-42')) AS expected_key
    UNION ALL
    SELECT
        'all_nulls_non_null_hash' AS case_name,
        CAST(NULL AS STRING) AS str_col,
        CAST(NULL AS INT64) AS int_col,
        TO_HEX(MD5('_null_-_null_')) AS expected_key
),

evaluated AS (
    SELECT
        case_name,
        {{ generate_surrogate_key(['str_col', 'int_col']) }} AS actual_key,
        expected_key
    FROM sample_inputs
)

SELECT
    case_name,
    actual_key,
    expected_key
FROM evaluated
WHERE
    actual_key IS NULL
    OR actual_key != expected_key
