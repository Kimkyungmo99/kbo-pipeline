"""수직 슬라이스 진입점: 경기 1개 → raw JSON 보존 → Parquet.

사용:
    python -m ingestion.run <game_id> <YYYY-MM-DD>
    python -m ingestion.run --list <YYYY-MM-DD>        # 그 날짜 경기 목록/ID 확인
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx
import polars as pl
import yaml

from ingestion.parsers.portal import assert_seq_contiguous, extract_text_relays, parse_pitches

CFG_PATH = Path("config/sources.yaml")


def load_cfg() -> dict:
    return yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))["portal"]


def get_json(url: str, cfg: dict) -> dict:
    r = httpx.get(url, headers=cfg["headers"], timeout=10, follow_redirects=True)
    r.raise_for_status()
    time.sleep(cfg["delay_seconds"])
    return r.json()


def list_games(date: str, cfg: dict) -> list[dict]:
    raw = get_json(cfg["game_list_url"].format(date=date), cfg)
    games = raw.get("result", {}).get("games", [])
    return games


def fetch_game(game_id: str, cfg: dict) -> dict:
    """relay 전체를 가져온다. 이닝별 분할 응답이면 1~12회를 루프로 병합."""
    base = cfg["pitch_url"].format(game_id=game_id)
    raw = get_json(base, cfg)

    merged = dict(raw)
    relays = extract_text_relays(raw)
    seen_innings = {r.get("inn") or r.get("inning") for r in relays}
    if len(seen_innings - {None}) <= 1:
        # 마지막 이닝만 온 것으로 판단 → 이닝별 수집 시도
        chunks = []
        for inning in range(1, 13):
            try:
                part = get_json(f"{base}?inning={inning}", cfg)
            except httpx.HTTPStatusError:
                break
            part_relays = extract_text_relays(part)
            if not part_relays:
                break
            chunks.append({"textRelays": part_relays})
        if chunks:
            merged = {"result": {"textRelayData": chunks}}
    return merged


def main() -> None:
    cfg = load_cfg()

    if sys.argv[1] == "--list":
        date = sys.argv[2]
        for g in list_games(date, cfg):
            print(g.get("gameId"), g.get("awayTeamName"), "vs", g.get("homeTeamName"),
                  "|", g.get("statusCode") or g.get("statusInfo"))
        return

    game_id, dt = sys.argv[1], sys.argv[2]
    raw = fetch_game(game_id, cfg)

    raw_dir = Path(f"data/raw/dt={dt}")
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"game_{game_id}.json").write_text(
        json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    rows = parse_pitches(raw, game_id)
    if not rows:
        print("파싱 결과 0행 — 응답 구조가 예상과 다름. raw JSON 최상위 키:")
        print(list(raw.keys()), "| result 키:", list(raw.get("result", {}).keys()))
        sys.exit(1)

    assert_seq_contiguous(rows)
    df = pl.DataFrame(rows)
    bronze_dir = Path(f"data/bronze/dt={dt}")
    bronze_dir.mkdir(parents=True, exist_ok=True)
    df.write_parquet(bronze_dir / "pitches.parquet", compression="zstd")
    print(f"OK: {len(df)} pitches -> {bronze_dir/'pitches.parquet'}")


if __name__ == "__main__":
    main()
