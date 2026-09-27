with pitching_duplicates as (
    select season, game_type, team_code
    from {{ ref('agg_team_pitching_season') }}
    group by 1, 2, 3 having count(*) != 1
),
batting_duplicates as (
    select season, game_type, team_code
    from {{ ref('agg_team_batting_season') }}
    group by 1, 2, 3 having count(*) != 1
)
select 'pitching' as model_name, * from pitching_duplicates
union all
select 'batting' as model_name, * from batting_duplicates
