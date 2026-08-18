"""인제스천 진입점.

사용:
    python -m ingestion.run <game_id> <YYYY-MM-DD>   # 경기 1개 (수직 슬라이스)
    python -m ingestion.run --date <YYYY-MM-DD>      # 그날 전 경기 (D4)
    python -m ingestion.run --list <YYYY-MM-DD>      # 경기 목록/상태 확인
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
    time.sleep(cfg["delay_seconds"])  # 수집 예의: 요청 간 최소 1초 (계획서 4장)
    return r.json()


def list_games(date: str, cfg: dict) -> list[dict]:
    raw = get_json(cfg["game_list_url"].format(date=date), cfg)
    return raw.get("result", {}).get("games", [])


def fetch_game(game_id: str, cfg: dict) -> dict:
    """relay 전체를 가져온다. 이닝별 분할 응답이면 1~12회를 루프로 병합."""
    base = cfg["pitch_url"].format(game_id=game_id)
    raw = get_json(base, cfg)

    merged = dict(raw)
    relays = extract_text_relays(raw)
    seen_innings = {r.get("inn") or r.get("inning") for r in relays}
    if len(seen_innings - {None}) <= 1:
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


def load_or_fetch_raw(game_id: str, dt: str, cfg: dict) -> dict:
    """이미 수집한 경기는 재요청하지 않는다 (수집 예의). raw 파일이 캐시."""
    raw_path = Path(f"data/raw/dt={dt}") / f"game_{game_id}.json"
    if raw_path.exists():
        print(f"  {game_id}: raw 캐시 사용")
        return json.loads(raw_path.read_text(encoding="utf-8"))
    raw = fetch_game(game_id, cfg)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return raw


def ingest_game(game_id: str, dt: str, cfg: dict) -> list[dict]:
    raw = load_or_fetch_raw(game_id, dt, cfg)
    rows = parse_pitches(raw, game_id)
    assert_seq_contiguous(rows)
    return rows


def write_bronze(rows: list[dict], dt: str) -> Path:
    df = pl.DataFrame(rows)
    bronze_dir = Path(f"data/bronze/dt={dt}")
    bronze_dir.mkdir(parents=True, exist_ok=True)
    out = bronze_dir / "pitches.parquet"
    df.write_parquet(out, compression="zstd")
    return out


def main() -> None:
    cfg = load_cfg()
    mode = sys.argv[1]

    if mode == "--list":
        for g in list_games(sys.argv[2], cfg):
            print(g.get("gameId"), g.get("categoryId"), g.get("awayTeamName"), "vs",
                  g.get("homeTeamName"), "|", g.get("statusCode") or g.get("statusInfo"))
        return

    if mode == "--date":
        dt = sys.argv[2]
        games = list_games(dt, cfg)
        # 필터 2종 (모두 실측으로 확인된 규칙):
        # 1) categoryId == "kbo" — upperCategoryId=kbaseball에는 퓨처스 등 비KBO 경기가
        #    섞이며, 그런 경기는 RESULT여도 투구 단위 relay가 없다 (0 pitches)
        # 2) statusCode == "RESULT" — 취소 경기(cancel:true)는 relay가 null
        done = [g for g in games
                if g.get("categoryId") == "kbo" and g.get("statusCode") == "RESULT"]
        print(f"{dt}: 전체 {len(games)}경기, 수집 대상(KBO·RESULT) {len(done)}경기")
        all_rows: list[dict] = []
        for g in done:
            rows = ingest_game(g["gameId"], dt, cfg)
            print(f"  {g['gameId']}: {len(rows)} pitches")
            if not rows:
                print(f"  경고: {g['gameId']} 투구 0건 — relay 구조 확인 필요")
            all_rows.extend(rows)
        if not all_rows:
            print("수집된 투구 없음")
            sys.exit(1)
        out = write_bronze(all_rows, dt)
        print(f"OK: {len(done)} games, {len(all_rows)} pitches -> {out}")
        return

    # 기본: 경기 1개
    game_id, dt = mode, sys.argv[2]
    rows = ingest_game(game_id, dt, cfg)
    if not rows:
        print("파싱 결과 0행 — 응답 구조 확인 필요")
        sys.exit(1)
    out = write_bronze(rows, dt)
    print(f"OK: {len(rows)} pitches -> {out}")


if __name__ == "__main__":
    main()
