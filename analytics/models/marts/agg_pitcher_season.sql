with pitch_metrics as (
    select
        season,
        game_type,
        pitcher_id as player_id,
        count(distinct game_id) as game_count,
        count(*) as pitch_count,
        count(*) filter (where velocity > 0) as measured_velocity_count,
        avg(velocity) filter (where velocity > 0) as avg_velocity,
        count(*) filter (where pitch_result = 'B') as ball_count,
        count(*) filter (where pitch_result = 'T') as called_strike_count,
        count(*) filter (where pitch_result = 'S') as swinging_strike_count,
        count(*) filter (where pitch_result = 'F') as foul_count,
        count(*) filter (where pitch_result = 'H') as in_play_count,
        count(*) filter (where pitch_result in ('S', 'F', 'H')) as swing_count
    from {{ ref('fct_pitches') }}
    group by season, game_type, pitcher_id
),
plate_appearance_metrics as (
    select
        season,
        game_type,
        pitcher_id as player_id,
        count(*) as plate_appearance_count,
        count(*) filter (where plate_appearance_result != 'unknown') as known_plate_appearance_count,
        count(*) filter (where plate_appearance_result = 'strikeout') as strikeout_count,
        count(*) filter (where plate_appearance_result = 'walk') as walk_count,
        count(*) filter (where plate_appearance_result = 'intentional_walk') as intentional_walk_count,
        count(*) filter (where plate_appearance_result = 'hit_by_pitch') as hit_by_pitch_count,
        count(*) filter (where plate_appearance_result in ('single', 'double', 'triple', 'home_run')) as hit_count,
        count(*) filter (where plate_appearance_result = 'home_run') as home_run_count
    from {{ ref('fct_pitches') }}
    where is_terminal_pitch
    group by season, game_type, pitcher_id
)
select
    pitch_metrics.*,
    plate_appearance_metrics.plate_appearance_count,
    plate_appearance_metrics.known_plate_appearance_count,
    plate_appearance_metrics.strikeout_count,
    plate_appearance_metrics.walk_count,
    plate_appearance_metrics.intentional_walk_count,
    plate_appearance_metrics.hit_by_pitch_count,
    plate_appearance_metrics.hit_count,
    plate_appearance_metrics.home_run_count,
    pitch_metrics.swinging_strike_count::double / nullif(pitch_metrics.swing_count, 0) as whiff_per_swing,
    plate_appearance_metrics.strikeout_count::double
        / nullif(plate_appearance_metrics.known_plate_appearance_count, 0) as strikeout_rate,
    plate_appearance_metrics.walk_count::double
        / nullif(plate_appearance_metrics.known_plate_appearance_count, 0) as walk_rate
from pitch_metrics
inner join plate_appearance_metrics using (season, game_type, player_id)
