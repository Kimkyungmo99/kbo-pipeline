with pitcher_activity as (
    select
        pitcher_id as player_id,
        min(game_date) as first_seen_date,
        max(game_date) as last_seen_date,
        count(distinct game_id) as pitcher_game_count,
        count(*) as pitches_thrown,
        0 as batter_game_count,
        0 as pitches_seen
    from {{ ref('fct_pitches') }}
    group by pitcher_id
),
batter_activity as (
    select
        batter_id as player_id,
        min(game_date) as first_seen_date,
        max(game_date) as last_seen_date,
        0 as pitcher_game_count,
        0 as pitches_thrown,
        count(distinct game_id) as batter_game_count,
        count(*) as pitches_seen
    from {{ ref('fct_pitches') }}
    group by batter_id
),
combined as (
    select * from pitcher_activity
    union all
    select * from batter_activity
),
player_observation_summary as (
    select
        player_id,
        arg_max(player_name, game_date) as player_name,
        min(game_date) as first_seen_date,
        max(game_date) as last_seen_date,
        bool_or(has_pitched) as has_pitched,
        bool_or(has_batted) as has_batted
    from {{ ref('stg_player_observations') }}
    group by player_id
),
player_activity as (
    select
        player_id,
        min(first_seen_date) as first_seen_date,
        max(last_seen_date) as last_seen_date,
        sum(pitcher_game_count) as pitcher_game_count,
        sum(batter_game_count) as batter_game_count,
        sum(pitches_thrown) as pitches_thrown,
        sum(pitches_seen) as pitches_seen
    from combined
    group by player_id
)
select
    coalesce(player_activity.player_id, player_observation_summary.player_id) as player_id,
    player_observation_summary.player_name,
    least(player_activity.first_seen_date, player_observation_summary.first_seen_date) as first_seen_date,
    greatest(player_activity.last_seen_date, player_observation_summary.last_seen_date) as last_seen_date,
    coalesce(player_activity.pitcher_game_count, 0) as pitcher_game_count,
    coalesce(player_activity.batter_game_count, 0) as batter_game_count,
    coalesce(player_activity.pitches_thrown, 0) as pitches_thrown,
    coalesce(player_activity.pitches_seen, 0) as pitches_seen,
    coalesce(player_activity.pitches_thrown, 0) > 0
        or coalesce(player_observation_summary.has_pitched, false) as has_pitched,
    coalesce(player_activity.pitches_seen, 0) > 0
        or coalesce(player_observation_summary.has_batted, false) as has_batted
from player_activity
full outer join player_observation_summary using (player_id)
