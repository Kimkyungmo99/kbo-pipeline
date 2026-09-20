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
)
select
    player_id,
    min(first_seen_date) as first_seen_date,
    max(last_seen_date) as last_seen_date,
    sum(pitcher_game_count) as pitcher_game_count,
    sum(batter_game_count) as batter_game_count,
    sum(pitches_thrown) as pitches_thrown,
    sum(pitches_seen) as pitches_seen,
    sum(pitches_thrown) > 0 as has_pitched,
    sum(pitches_seen) > 0 as has_batted
from combined
group by player_id
