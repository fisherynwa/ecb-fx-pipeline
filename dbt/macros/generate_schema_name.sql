{#
  By default dbt would name the schemas "main_silver" and "main_gold"
  (default schema + "_" + the name from dbt_project.yml).
  This macro tells dbt to use exactly the name we wrote: "silver", "gold".
  Copied from the dbt documentation; you rarely need to change it.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
