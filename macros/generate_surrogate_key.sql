{% macro generate_surrogate_key(field_list) %}
{#-
    PURPOSE: Generates a deterministic MD5 surrogate key hash across a list of columns.
    COMPATIBILITY: Google Cloud BigQuery (Standard SQL)
    USAGE: {{ generate_surrogate_key(['user_id', 'lesson_id']) }} AS assignment_sk
-#}
{%- set field_expressions = [] -%}

{%- for field in field_list -%}
    {%- do field_expressions.append("COALESCE(CAST(" ~ field ~ " AS STRING), '_null_')") -%}
    {%- if not loop.last -%}
        {%- do field_expressions.append("'-'") -%}
    {%- endif -%}
{%- endfor -%}

TO_HEX(MD5(CONCAT({{ field_expressions | join(', ') }})))

{% endmacro %}
