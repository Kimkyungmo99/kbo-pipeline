with fact_total as (
    select count(*) as pitch_count
    from {{ ref('fct_pitches') }}
),
model_totals as (
    select 'pitcher' as model_name, sum(pitch_count) as pitch_count
    from {{ ref('agg_pitcher_season') }}
    union all
    select 'batter' as model_name, sum(pitch_count) as pitch_count
    from {{ ref('agg_batter_season') }}
)
select model_totals.*
from model_totals
cross join fact_total
where model_totals.pitch_count != fact_total.pitch_count
