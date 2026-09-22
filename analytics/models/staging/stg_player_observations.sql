with observations as (
    select
        cast(game_date as date) as game_date,
        cast(year(game_date) as integer) as season,
        player_id,
        player_name,
        team_code,
        has_pitched,
        has_batted,
        game_count
    from read_parquet('../data/bronze_players/dt=*/players.parquet')
),
known_names as (
    select
        player_id,
        arg_max(player_name, game_date) as player_name
    from observations
    where player_name is not null
    group by player_id
)
select
    observations.game_date,
    observations.season,
    observations.player_id,
    known_names.player_name,
    observations.team_code,
    observations.has_pitched,
    observations.has_batted,
    observations.game_count
from observations
left join known_names using (player_id)
