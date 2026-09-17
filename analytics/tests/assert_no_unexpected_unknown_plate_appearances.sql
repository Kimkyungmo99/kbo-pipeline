select plate_appearances.*
from {{ ref('int_plate_appearances') }} as plate_appearances
left join {{ ref('known_incomplete_plate_appearances') }} as known
    on plate_appearances.game_id = known.game_id
   and plate_appearances.ending_pitch_seq_in_game = known.ending_pitch_seq_in_game
where plate_appearances.plate_appearance_result = 'unknown'
  and known.game_id is null
