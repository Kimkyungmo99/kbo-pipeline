with transitions as (
    select
        game_id,
        pitch_seq_in_game,
        is_plate_appearance_start,
        balls_after_event,
        strikes_after_event,
        balls_after_event - lag(balls_after_event) over game_events as delta_balls,
        strikes_after_event - lag(strikes_after_event) over game_events as delta_strikes
    from {{ ref('stg_pitch_events') }}
    window game_events as (
        partition by game_id
        order by pitch_seq_in_game
    )
),

violations as (
    select *
    from transitions
    where (
        is_plate_appearance_start
        and (balls_after_event, strikes_after_event) not in ((0, 0), (0, 1), (1, 0))
    ) or (
        not is_plate_appearance_start
        and (
            (delta_balls, delta_strikes) not in ((1, 0), (0, 1), (0, 0))
            or balls_after_event > 4
            or strikes_after_event > 3
        )
    )
)

select violations.*
from violations
left join {{ ref('known_count_transition_violations') }} as known
    on violations.game_id = known.game_id
   and violations.pitch_seq_in_game = known.pitch_seq_in_game
where known.game_id is null
