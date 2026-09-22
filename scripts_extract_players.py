"""보존된 relay raw에서 날짜별 선수 이름·소속·역할 관측을 재구성한다.

사용:
    py scripts_extract_players.py             # 로컬 raw 전체
    py scripts_extract_players.py 2026-09-22  # 한 날짜만 처리
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import polars as pl

from ingestion import storage
from ingestion.gametype import TARGET_GAME_TYPES, classify_game_type
from ingestion.run import get_s3_or_none

RAW_ROOT = Path("data/raw/source=portal")
OUT_ROOT = Path("data/bronze_players")
PITCHER_CHANGE = re.compile(r"투수 (.+?) : 투수 (.+?) \(으\)로 교체")


def collect_names(value: object, names: dict[str, str]) -> None:
    if isinstance(value, dict):
        pairs = (
            (value.get("pcode"), value.get("name")),
            (value.get("playerId"), value.get("playerName")),
        )
        for player_id, player_name in pairs:
            if player_id and player_name:
                names[str(player_id)] = str(player_name)
        for child in value.values():
            collect_names(child, names)
    elif isinstance(value, list):
        for child in value:
            collect_names(child, names)


def infer_unstructured_pitcher_names(raw: dict, names: dict[str, str]) -> None:
    """일부 외국인 교체 이벤트는 이름만 있고 playerId가 없다.

    seqno 순서에서 교체 직전·직후 pitcher ID와 교체 문구를 결합해 복원한다.
    """
    options = []
    for group in raw.get("result", {}).get("textRelayData", []) or []:
        for relay in group.get("textRelays", []) or []:
            options.extend(relay.get("textOptions", []) or [])

    previous_pitcher_id = None
    for option in sorted(options, key=lambda item: int(item.get("seqno") or 0)):
        state = option.get("currentGameState") or {}
        current_pitcher_id = state.get("pitcher")
        match = PITCHER_CHANGE.fullmatch(str(option.get("text") or ""))
        if match and current_pitcher_id:
            outgoing_name, incoming_name = match.groups()
            if previous_pitcher_id and str(previous_pitcher_id) != str(current_pitcher_id):
                names.setdefault(str(previous_pitcher_id), outgoing_name)
            names.setdefault(str(current_pitcher_id), incoming_name)
        if current_pitcher_id:
            previous_pitcher_id = current_pitcher_id


def extract_game(path: Path) -> tuple[dict[str, str], set[tuple[str, str, str]]]:
    game_id = path.stem.removeprefix("game_")
    away_team, home_team = game_id[8:10], game_id[10:12]
    raw = json.loads(path.read_text(encoding="utf-8"))
    names: dict[str, str] = {}
    collect_names(raw, names)
    infer_unstructured_pitcher_names(raw, names)
    observations: set[tuple[str, str, str]] = set()

    for group in raw.get("result", {}).get("textRelayData", []) or []:
        for relay in group.get("textRelays", []) or []:
            half = str(relay.get("homeOrAway"))
            if half not in {"0", "1"}:
                continue
            batter_team = away_team if half == "0" else home_team
            pitcher_team = home_team if half == "0" else away_team
            for option in relay.get("textOptions", []) or []:
                if option.get("pitchNum") is None or option.get("pitchResult") is None:
                    continue
                state = option.get("currentGameState") or {}
                pitcher_id = state.get("pitcher")
                batter_id = state.get("batter")
                if pitcher_id:
                    observations.add((str(pitcher_id), pitcher_team, "pitcher"))
                if batter_id:
                    observations.add((str(batter_id), batter_team, "batter"))
    return names, observations


def extract_date(dt_dir: Path, s3=None) -> tuple[int, int]:
    dt = dt_dir.name.removeprefix("dt=")
    names: dict[str, str] = {}
    games_by_player: dict[tuple[str, str, str], set[str]] = defaultdict(set)

    paths = [
        path for path in sorted(dt_dir.glob("game_*.json"))
        if classify_game_type(path.stem.removeprefix("game_")) in TARGET_GAME_TYPES
    ]
    for path in paths:
        game_names, observations = extract_game(path)
        names.update(game_names)
        game_id = path.stem.removeprefix("game_")
        for observation in observations:
            games_by_player[observation].add(game_id)

    if not games_by_player:
        print(f"[{dt}] 선수 관측 없음")
        return len(paths), 0

    grouped: dict[tuple[str, str], dict] = {}
    for (player_id, team_code, role), game_ids in games_by_player.items():
        key = (player_id, team_code)
        row = grouped.setdefault(key, {
            "game_date": dt,
            "player_id": player_id,
            "player_name": names.get(player_id),
            "team_code": team_code,
            "has_pitched": False,
            "has_batted": False,
            "game_ids": set(),
        })
        row["has_pitched"] |= role == "pitcher"
        row["has_batted"] |= role == "batter"
        row["game_ids"].update(game_ids)

    rows = [{
        "game_date": row["game_date"],
        "player_id": row["player_id"],
        "player_name": row["player_name"],
        "team_code": row["team_code"],
        "has_pitched": row["has_pitched"],
        "has_batted": row["has_batted"],
        "game_count": len(row["game_ids"]),
    } for row in grouped.values()]

    out = OUT_ROOT / f"dt={dt}" / "players.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).with_columns(pl.col("game_date").str.to_date()).write_parquet(out, compression="zstd")
    if s3 is not None:
        storage.upload_file(s3, out, f"bronze_players/dt={dt}/players.parquet")
    print(f"[{dt}] {len(paths)}경기, 선수·팀 관측 {len(rows)}행")
    return len(paths), len(rows)


def main() -> None:
    requested = sys.argv[1] if len(sys.argv) > 1 else None
    date_dirs = [RAW_ROOT / f"dt={requested}"] if requested else sorted(RAW_ROOT.glob("dt=*"))
    s3 = get_s3_or_none()
    game_total = row_total = 0
    for date_dir in date_dirs:
        if not date_dir.exists():
            print(f"[{requested}] raw 없음 — 정상 종료")
            continue
        games, rows = extract_date(date_dir, s3=s3)
        game_total += games
        row_total += rows
    print(f"완료: {game_total}경기, 선수·팀 관측 {row_total}행")


if __name__ == "__main__":
    main()
