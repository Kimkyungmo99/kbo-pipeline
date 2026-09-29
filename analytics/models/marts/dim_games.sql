select
    cast(game_date as date) as game_date,
    game_id,
    season,
    game_type,
    away_team_code,
    home_team_code,
    away_score,
    home_score,
    winner,
    home_score + away_score as total_runs,
    home_score - away_score as home_run_differential
from read_parquet(
    '../data/bronze_games/dt=*/games.parquet',
    hive_partitioning = true
)
