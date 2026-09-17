select
    game_id,
    pitch_seq_in_game,
    count(*) as row_count
from {{ ref('fct_pitches') }}
group by game_id, pitch_seq_in_game
having count(*) != 1
