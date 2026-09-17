select
    game_id,
    plate_appearance_number,
    count(*) as row_count
from {{ ref('int_plate_appearances') }}
group by game_id, plate_appearance_number
having count(*) != 1
