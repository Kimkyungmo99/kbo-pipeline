select
    season,
    game_type,
    pitch_type,
    balls_before_pitch,
    strikes_before_pitch,
    count(*) as row_count
from {{ ref('agg_pitch_type_count') }}
group by 1, 2, 3, 4, 5
having count(*) != 1
