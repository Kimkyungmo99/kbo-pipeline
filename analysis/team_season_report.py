"""Build a reproducible 2024-2025 KBO regular-season team comparison."""

from __future__ import annotations

import csv
import html
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "analytics" / "kbo_analytics.duckdb"
OUTPUT_DIR = ROOT / "analysis" / "outputs"
CSV_PATH = OUTPUT_DIR / "team_regular_2024_2025.csv"
SVG_PATH = OUTPUT_DIR / "team_regular_2024_2025.svg"
REPORT_PATH = OUTPUT_DIR / "team_regular_2024_2025.md"

QUERY = """
select
    batting.season,
    batting.team_code,
    batting.team_name,
    batting.game_count,
    batting.plate_appearance_count,
    batting.hit_count,
    batting.home_run_count,
    batting.home_run_count::double / batting.game_count as home_runs_per_game,
    batting.strikeout_rate as batting_strikeout_rate,
    batting.walk_rate as batting_walk_rate,
    batting.whiff_per_swing as batting_whiff_rate,
    pitching.avg_velocity,
    pitching.strikeout_rate as pitching_strikeout_rate,
    pitching.walk_rate as pitching_walk_rate,
    pitching.whiff_per_swing as pitching_whiff_rate,
    pitching.hit_count as hits_allowed,
    pitching.home_run_count as home_runs_allowed
from agg_team_batting_season as batting
inner join agg_team_pitching_season as pitching
    using (season, game_type, team_code)
where batting.game_type = 'regular'
  and batting.season in (2024, 2025)
order by batting.season, batting.team_code
"""

COLUMNS = [
    "season", "team_code", "team_name", "game_count", "plate_appearance_count",
    "hit_count", "home_run_count", "home_runs_per_game", "batting_strikeout_rate",
    "batting_walk_rate", "batting_whiff_rate", "avg_velocity",
    "pitching_strikeout_rate", "pitching_walk_rate", "pitching_whiff_rate",
    "hits_allowed", "home_runs_allowed",
]

METRICS = [
    ("home_runs_per_game", "Home runs per game", "{:.2f}", True),
    ("batting_strikeout_rate", "Batting strikeout rate", "{:.1%}", False),
    ("batting_walk_rate", "Batting walk rate", "{:.1%}", True),
    ("avg_velocity", "Average pitch velocity (km/h)", "{:.1f}", True),
]


def load_rows() -> list[dict]:
    with duckdb.connect(str(DATABASE), read_only=True) as connection:
        values = connection.execute(QUERY).fetchall()
    return [dict(zip(COLUMNS, row, strict=True)) for row in values]


def write_csv(rows: list[dict]) -> None:
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def svg_text(x: float, y: float, value: str, **attrs: object) -> str:
    properties = " ".join(f'{key.replace("_", "-")}="{html.escape(str(val))}"' for key, val in attrs.items())
    return f'<text x="{x:.1f}" y="{y:.1f}" {properties}>{html.escape(value)}</text>'


def write_svg(rows: list[dict]) -> None:
    current = [row for row in rows if row["season"] == 2025]
    width, height = 1400, 980
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#F7F8FA"/>',
        svg_text(64, 65, "KBO TEAM COMPARISON", fill="#111827", font_size=30, font_weight="700"),
        svg_text(64, 98, "2025 regular season · rates and per-game metrics", fill="#5B6472", font_size=17),
        svg_text(1336, 65, "DATA THROUGH 2025 SEASON", fill="#697386", font_size=13, text_anchor="end"),
    ]

    panel_width, panel_height = 620, 360
    positions = [(64, 135), (716, 135), (64, 535), (716, 535)]
    navy, orange, grid = "#2457A7", "#E87932", "#DDE2E8"

    for (metric, title, formatter, higher_is_better), (left, top) in zip(METRICS, positions, strict=True):
        ordered = sorted(current, key=lambda row: row[metric], reverse=True)
        values = [float(row[metric]) for row in ordered]
        minimum, maximum = min(values), max(values)
        span = maximum - minimum or 1
        parts.append(f'<rect x="{left}" y="{top}" width="{panel_width}" height="{panel_height}" rx="14" fill="#FFFFFF" stroke="#E4E7EB"/>')
        parts.append(svg_text(left + 28, top + 38, title, fill="#1F2937", font_size=19, font_weight="700"))
        direction = "higher is better" if higher_is_better else "lower is better"
        parts.append(svg_text(left + panel_width - 28, top + 38, direction, fill="#7A8493", font_size=12, text_anchor="end"))
        chart_left, chart_right = left + 82, left + panel_width - 78
        chart_top = top + 66
        for index, row in enumerate(ordered):
            y = chart_top + index * 27
            value = float(row[metric])
            bar_width = 70 + ((value - minimum) / span) * (chart_right - chart_left - 70)
            color = orange if index == 0 else navy
            parts.append(svg_text(chart_left - 13, y + 14, row["team_code"], fill="#374151", font_size=13, font_weight="700", text_anchor="end"))
            parts.append(f'<line x1="{chart_left}" y1="{y + 10}" x2="{chart_right}" y2="{y + 10}" stroke="{grid}" stroke-width="1"/>')
            parts.append(f'<rect x="{chart_left}" y="{y + 3}" width="{bar_width:.1f}" height="14" rx="7" fill="{color}"/>')
            parts.append(svg_text(chart_left + bar_width + 8, y + 15, formatter.format(value), fill="#263140", font_size=12, font_weight="600"))
        parts.append(svg_text(left + 28, top + panel_height - 18, "Ranked among 10 teams", fill="#98A1AD", font_size=11))

    parts.extend([
        svg_text(64, 942, "Source: kbo-pipeline / agg_team_batting_season + agg_team_pitching_season", fill="#7A8493", font_size=12),
        svg_text(1336, 942, "Team codes used for font-safe labels", fill="#7A8493", font_size=12, text_anchor="end"),
        "</svg>",
    ])
    SVG_PATH.write_text("\n".join(parts), encoding="utf-8")


def pct_change(current: float, previous: float) -> float:
    return (current / previous - 1) * 100


def write_report(rows: list[dict]) -> None:
    by_key = {(row["season"], row["team_code"]): row for row in rows}
    current = [row for row in rows if row["season"] == 2025]
    best_hr = max(current, key=lambda row: row["home_runs_per_game"])
    best_contact = min(current, key=lambda row: row["batting_strikeout_rate"])
    best_walk = max(current, key=lambda row: row["batting_walk_rate"])
    fastest = max(current, key=lambda row: row["avg_velocity"])
    fastest_2024 = by_key[(2024, fastest["team_code"])]
    report = f"""# 2024–2025 KBO 정규시즌 팀 비교

## 핵심 결과

- **경기당 홈런 1위:** {best_hr['team_name']}({best_hr['team_code']}) {best_hr['home_runs_per_game']:.2f}개.
- **타격 삼진율 최저:** {best_contact['team_name']}({best_contact['team_code']}) {best_contact['batting_strikeout_rate']:.1%}.
- **타격 볼넷율 최고:** {best_walk['team_name']}({best_walk['team_code']}) {best_walk['batting_walk_rate']:.1%}.
- **평균 투구 구속 1위:** {fastest['team_name']}({fastest['team_code']}) {fastest['avg_velocity']:.1f}km/h. 2024년 {fastest_2024['avg_velocity']:.1f}km/h에서 {pct_change(fastest['avg_velocity'], fastest_2024['avg_velocity']):+.1f}% 변했다.

## 해석 범위

- 팀마다 경기 수가 달라 홈런은 합계 대신 경기당 수치로 비교했다.
- 삼진율과 볼넷율의 분모는 결과를 분류할 수 있는 타석이다.
- 평균 구속은 구속이 0보다 큰 투구만 포함한다.
- 이 결과는 기술적 분석의 첫 단계다. 팀 성과를 설명하려면 득점·실점, 구장, 상대 팀, 선수 구성 같은 맥락을 추가해야 한다.

## 산출물

- `team_regular_2024_2025.svg`: 2025년 네 가지 팀 지표 순위.
- `team_regular_2024_2025.csv`: 2024·2025년 팀별 비교 데이터.
- 생성 명령: `py analysis/team_season_report.py`
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    if len(rows) != 20:
        raise ValueError(f"Expected 20 team-season rows, found {len(rows)}")
    write_csv(rows)
    write_svg(rows)
    write_report(rows)
    print(f"Created {CSV_PATH.relative_to(ROOT)}, {SVG_PATH.relative_to(ROOT)}, and {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
