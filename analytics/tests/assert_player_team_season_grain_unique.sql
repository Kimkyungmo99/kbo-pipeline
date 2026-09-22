select
    season,
    player_id,
    team_code,
    count(*) as row_count
from {{ ref('dim_player_team_seasons') }}
group by 1, 2, 3
having count(*) != 1
