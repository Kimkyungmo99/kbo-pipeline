with team_games as (
    select
        season,
        game_type,
        game_id,
        away_team_code as team_code,
        away_score as runs_scored,
        home_score as runs_allowed,
        winner = 'AWAY' as is_win,
        winner = 'HOME' as is_loss,
        winner = 'DRAW' as is_draw
    from {{ ref('dim_games') }}

    union all

    select
        season,
        game_type,
        game_id,
        home_team_code as team_code,
        home_score as runs_scored,
        away_score as runs_allowed,
        winner = 'HOME' as is_win,
        winner = 'AWAY' as is_loss,
        winner = 'DRAW' as is_draw
    from {{ ref('dim_games') }}
),

aggregated as (
    select
        season,
        game_type,
        team_code,
        count(*) as game_count,
        count(*) filter (where is_win) as win_count,
        count(*) filter (where is_loss) as loss_count,
        count(*) filter (where is_draw) as draw_count,
        sum(runs_scored) as runs_scored,
        sum(runs_allowed) as runs_allowed
    from team_games
    group by season, game_type, team_code
)

select
    aggregated.*,
    team_codes.team_name,
    aggregated.win_count::double / nullif(aggregated.win_count + aggregated.loss_count, 0) as win_rate,
    aggregated.runs_scored - aggregated.runs_allowed as run_differential,
    (aggregated.runs_scored - aggregated.runs_allowed)::double / aggregated.game_count as run_differential_per_game
from aggregated
inner join {{ ref('team_codes') }} as team_codes using (team_code)
