with metric_total as (
    select sum(pitch_count) as pitch_count
    from {{ ref('agg_pitch_type_count') }}
),
fact_total as (
    select count(*) as pitch_count
    from {{ ref('fct_pitches') }}
)
select metric_total.pitch_count, fact_total.pitch_count
from metric_total
cross join fact_total
where metric_total.pitch_count != fact_total.pitch_count
