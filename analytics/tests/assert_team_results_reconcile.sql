with games as (
    select season, game_type, count(*) * 2 as expected_team_games
    from {{ ref('dim_games') }}
    group by season, game_type
),
team_results as (
    select
        season,
        game_type,
        sum(game_count) as actual_team_games,
        sum(runs_scored) as runs_scored,
        sum(runs_allowed) as runs_allowed
    from {{ ref('agg_team_results_season') }}
    group by season, game_type
)
select games.season, games.game_type
from games
inner join team_results using (season, game_type)
where games.expected_team_games != team_results.actual_team_games
   or team_results.runs_scored != team_results.runs_allowed
