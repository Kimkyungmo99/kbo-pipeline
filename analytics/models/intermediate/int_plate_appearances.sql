with events as (
    select *
    from {{ ref('stg_pitch_events') }}
),

one_row_per_plate_appearance as (
    select
        game_date,
        game_id,
        game_type,
        plate_appearance_number,
        arg_min(inning, pitch_seq_in_game) as inning,
        arg_min(is_top, pitch_seq_in_game) as is_top,
        arg_max(pitcher_id, pitch_seq_in_game) as pitcher_id,
        arg_max(batter_id, pitch_seq_in_game) as batter_id,
        count(*) as event_count,
        count(*) filter (where event_type = 'pitch') as pitch_count,
        max(pitch_seq_in_game) as ending_pitch_seq_in_game,
        arg_max(outs, pitch_seq_in_game) as outs_after,
        arg_max(result, pitch_seq_in_game) as ending_pitch_result,
        arg_max(following_text, pitch_seq_in_game) as result_text
    from events
    group by
        game_date,
        game_id,
        game_type,
        plate_appearance_number
),

classified as (
    select
        *,
        case
            when contains(result_text, '몸에 맞는 볼') then 'hit_by_pitch'
            when contains(result_text, '자동 고의4구') then 'intentional_walk'
            when contains(result_text, '볼넷') then 'walk'
            when contains(result_text, '삼진') then 'strikeout'
            when contains(result_text, '홈런') then 'home_run'
            when contains(result_text, '3루타') then 'triple'
            when contains(result_text, '2루타') then 'double'
            when contains(result_text, '1루타') then 'single'
            when contains(result_text, '안타') then 'single'
            when contains(result_text, '희생') then 'sacrifice'
            when contains(result_text, '야수선택')
              or contains(result_text, '야수 선택')
              or contains(result_text, '땅볼로 출루') then 'fielders_choice'
            when contains(result_text, '실책') then 'reached_on_error'
            when contains(result_text, '아웃') then 'out'
            else 'unknown'
        end as plate_appearance_result
    from one_row_per_plate_appearance
)

select *
from classified
