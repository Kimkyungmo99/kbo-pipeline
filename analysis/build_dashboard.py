"""Generate an offline team dashboard from the current local dbt snapshot."""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis/outputs/kbo_team_dashboard.html"

QUERY = """
select r.*, b.game_count as batting_game_count,
    p.game_count as pitching_game_count,
    b.home_run_count, b.known_plate_appearance_count,
    b.home_run_count::double / b.game_count as home_runs_per_game,
    b.strikeout_rate as batting_strikeout_rate,
    b.walk_rate as batting_walk_rate,
    b.whiff_per_swing as batting_whiff_rate,
    p.avg_velocity, p.measured_velocity_count,
    p.strikeout_rate as pitching_strikeout_rate,
    p.walk_rate as pitching_walk_rate,
    p.whiff_per_swing as pitching_whiff_rate
from agg_team_results_season r
left join agg_team_batting_season b using (season, game_type, team_code)
left join agg_team_pitching_season p using (season, game_type, team_code)
where r.game_type = 'regular' and r.season in (2024, 2025)
order by r.season, r.team_code
"""


def validate_rows(rows: list[dict], seasons: list[dict]) -> None:
    keys = [(r["season"], r["team_code"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate team-season grain")
    for r in rows:
        for name, value in r.items():
            if value is None or isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"Missing or invalid value: {r['team_code']} {name}")
        if r["game_count"] != r["batting_game_count"] or r["game_count"] != r["pitching_game_count"]:
            raise ValueError("Results and pitch metrics cover different games")
        if r["game_count"] != r["win_count"] + r["loss_count"] + r["draw_count"]:
            raise ValueError("W/L/D does not reconcile")
    for season in seasons:
        group = [r for r in rows if r["season"] == season["season"]]
        if len(group) != 10 or sum(r["game_count"] for r in group) != 2 * season["games"]:
            raise ValueError("Team counts do not reconcile with games")
        if sum(r["runs_scored"] for r in group) != sum(r["runs_allowed"] for r in group):
            raise ValueError("Runs scored and allowed do not reconcile")


def main() -> None:
    import duckdb

    with duckdb.connect(str(ROOT / "analytics/kbo_analytics.duckdb"), read_only=True) as con:
        result = con.execute(QUERY)
        columns = [c[0] for c in result.description]
        rows = [dict(zip(columns, r, strict=True)) for r in result.fetchall()]
        seasons = [dict(zip(["season", "games", "first_date", "last_date"], r, strict=True)) for r in con.execute("""
            select season, count(*), cast(min(game_date) as varchar), cast(max(game_date) as varchar)
            from dim_games where game_type = 'regular' and season in (2024, 2025)
            group by season order by season
        """).fetchall()]
    if sorted(s["season"] for s in seasons) != [2024, 2025]:
        raise ValueError("Both comparison seasons must be present")
    validate_rows(rows, seasons)
    payload = json.dumps({"rows": rows, "seasons": seasons}, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    template = (ROOT / "analysis/dashboard.html").read_text(encoding="utf-8")
    library = (ROOT / "analysis/vendor/chart.umd.min.js").read_text(encoding="utf-8")
    library = library.split("//# sourceMappingURL=")[0]
    if "</script" in library.lower():
        raise ValueError("Unsafe inline library content")
    output = template.replace("/*__CHART_LIBRARY__*/", library).replace("__DASHBOARD_PAYLOAD__", payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(output, encoding="utf-8")
    print(f"Built {len(rows)} team-seasons -> {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
