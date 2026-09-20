with pitches as (
    select
        season,
        game_type,
        coalesce(pitch_type, '미분류') as pitch_type,
        balls_before_pitch,
        strikes_before_pitch,
        velocity,
        pitch_result
    from {{ ref('fct_pitches') }}
)
select
    season,
    game_type,
    pitch_type,
    balls_before_pitch,
    strikes_before_pitch,
    count(*) as pitch_count,
    count(*) filter (where velocity > 0) as measured_velocity_count,
    avg(velocity) filter (where velocity > 0) as avg_velocity,
    count(*) filter (where pitch_result = 'B') as ball_count,
    count(*) filter (where pitch_result = 'T') as called_strike_count,
    count(*) filter (where pitch_result = 'S') as swinging_strike_count,
    count(*) filter (where pitch_result = 'F') as foul_count,
    count(*) filter (where pitch_result = 'H') as in_play_count,
    count(*) filter (where pitch_result in ('S', 'F', 'H')) as swing_count,
    count(*) filter (where pitch_result not in ('B', 'T', 'S', 'F', 'H')) as other_result_count,
    count(*) filter (where pitch_result = 'S')::double
        / nullif(count(*) filter (where pitch_result in ('S', 'F', 'H')), 0) as whiff_per_swing,
    count(*) filter (where pitch_result in ('T', 'S', 'F'))::double
        / count(*) as strike_result_rate
from pitches
group by
    season,
    game_type,
    pitch_type,
    balls_before_pitch,
    strikes_before_pitch
