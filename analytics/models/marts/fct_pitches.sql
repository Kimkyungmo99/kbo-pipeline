with pitch_events as (
    select *
    from {{ ref('stg_pitch_events') }}
    where event_type = 'pitch'
),

plate_appearances as (
    select
        game_id,
        plate_appearance_number,
        ending_pitch_seq_in_game,
        plate_appearance_result,
        result_text
    from {{ ref('int_plate_appearances') }}
),

joined as (
    select
        pitch_events.game_date,
        cast(right(pitch_events.game_id, 4) as integer) as season,
        pitch_events.game_id,
        pitch_events.game_type,
        pitch_events.pitch_seq_in_game,
        pitch_events.plate_appearance_number,
        row_number() over (
            partition by pitch_events.game_id, pitch_events.plate_appearance_number
            order by pitch_events.pitch_seq_in_game
        ) as pitch_number_in_plate_appearance,
        pitch_events.inning,
        pitch_events.is_top,
        pitch_events.pitcher_id,
        pitch_events.batter_id,
        pitch_events.balls_before_event as balls_before_pitch,
        pitch_events.strikes_before_event as strikes_before_pitch,
        pitch_events.balls_after_event as balls_after_pitch,
        pitch_events.strikes_after_event as strikes_after_pitch,
        pitch_events.outs,
        pitch_events.base1,
        pitch_events.base2,
        pitch_events.base3,
        pitch_events.score_home,
        pitch_events.score_away,
        pitch_events.pitch_type,
        pitch_events.velocity,
        pitch_events.result as pitch_result,
        pitch_events.text as pitch_text,
        pitch_events.following_text,
        pitch_events.pitch_seq_in_game = plate_appearances.ending_pitch_seq_in_game
            as is_terminal_pitch,
        plate_appearances.plate_appearance_result,
        plate_appearances.result_text as plate_appearance_result_text
    from pitch_events
    inner join plate_appearances
        on pitch_events.game_id = plate_appearances.game_id
       and pitch_events.plate_appearance_number = plate_appearances.plate_appearance_number
)

select
    *,
    game_type = 'regular' as is_regular_season,
    game_type = 'exhibition' as is_exhibition,
    game_type = 'tiebreaker' as is_tiebreaker,
    game_type in ('wildcard', 'semi_po', 'po', 'ks') as is_postseason
from joined
