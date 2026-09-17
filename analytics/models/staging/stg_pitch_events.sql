with bronze as (
    select
        cast(dt as date) as game_date,
        game_id,
        game_type,
        event_type,
        pitch_seq_in_game,
        inning,
        is_top,
        pitcher_id,
        batter_id,
        balls,
        strikes,
        outs,
        base1,
        base2,
        base3,
        score_home,
        score_away,
        pitch_type,
        velocity,
        result,
        text,
        following_text
    from read_parquet(
        '../data/bronze/dt=*/pitches.parquet',
        hive_partitioning = true
    )
),

with_previous as (
    select
        *,
        lag(inning) over game_events as previous_inning,
        lag(is_top) over game_events as previous_is_top,
        lag(batter_id) over game_events as previous_batter_id,
        lag(following_text) over game_events as previous_following_text,
        lag(balls) over game_events as previous_balls,
        lag(strikes) over game_events as previous_strikes
    from bronze
    window game_events as (
        partition by game_id
        order by pitch_seq_in_game
    )
),

marked_plate_appearances as (
    select
        *,
        previous_inning is null
        or inning is distinct from previous_inning
        or is_top is distinct from previous_is_top
        or (
            batter_id is distinct from previous_batter_id
            and not contains(coalesce(previous_following_text, ''), '대타')
        )
        or balls < previous_balls
        or strikes < previous_strikes
            as is_plate_appearance_start
    from with_previous
),

with_pre_pitch_state as (
    select
        *,
        sum(cast(is_plate_appearance_start as integer)) over (
            partition by game_id
            order by pitch_seq_in_game
            rows between unbounded preceding and current row
        ) as plate_appearance_number,
        case when is_plate_appearance_start then 0 else previous_balls end
            as balls_before_event,
        case when is_plate_appearance_start then 0 else previous_strikes end
            as strikes_before_event
    from marked_plate_appearances
)

select
    game_date,
    game_id,
    game_type,
    event_type,
    pitch_seq_in_game,
    plate_appearance_number,
    is_plate_appearance_start,
    inning,
    is_top,
    pitcher_id,
    batter_id,
    balls_before_event,
    strikes_before_event,
    balls as balls_after_event,
    strikes as strikes_after_event,
    outs,
    base1,
    base2,
    base3,
    score_home,
    score_away,
    pitch_type,
    velocity,
    result,
    text,
    following_text
from with_pre_pitch_state
