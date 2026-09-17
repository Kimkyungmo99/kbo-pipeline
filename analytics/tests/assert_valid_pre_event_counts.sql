select *
from {{ ref('stg_pitch_events') }}
where balls_before_event not between 0 and 3
   or strikes_before_event not between 0 and 2
