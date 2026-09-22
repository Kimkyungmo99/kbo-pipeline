select
    observations.season,
    observations.player_id,
    arg_max(observations.player_name, observations.game_date) as player_name,
    observations.team_code,
    team_codes.team_name,
    min(observations.game_date) as first_seen_date,
    max(observations.game_date) as last_seen_date,
    sum(observations.game_count) as game_count,
    bool_or(observations.has_pitched) as has_pitched,
    bool_or(observations.has_batted) as has_batted
from {{ ref('stg_player_observations') }} as observations
inner join {{ ref('team_codes') }} as team_codes using (team_code)
group by
    observations.season,
    observations.player_id,
    observations.team_code,
    team_codes.team_name
