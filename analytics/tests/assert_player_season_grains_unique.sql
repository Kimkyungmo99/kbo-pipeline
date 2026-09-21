with pitcher_duplicates as (
    select season, game_type, player_id
    from {{ ref('agg_pitcher_season') }}
    group by 1, 2, 3
    having count(*) != 1
),
batter_duplicates as (
    select season, game_type, player_id
    from {{ ref('agg_batter_season') }}
    group by 1, 2, 3
    having count(*) != 1
)
select 'pitcher' as model_name, * from pitcher_duplicates
union all
select 'batter' as model_name, * from batter_duplicates
