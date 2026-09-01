"""인제스천 CLI — 얇은 오케스트레이션만 한다. 소스 로직은 어댑터(portal.py)에.

사용:
    python -m ingestion.run <game_id> <YYYY-MM-DD>   # 경기 1개
    python -m ingestion.run --date <YYYY-MM-DD>      # 그날 전 경기 (KBO·RESULT)
    python -m ingestion.run --list <YYYY-MM-DD>      # 경기 목록/상태 확인
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import polars as pl
import yaml

from ingestion import storage
from ingestion.base import GameRef, GameSource
from ingestion.parsers.portal import assert_seq_contiguous
from ingestion.portal import PortalSource

CFG_PATH = Path("config/sources.yaml")


def get_s3_or_none():
    """R2 클라이언트. 자격증명(.env) 없으면 None — 로컬 전용 모드로 동작."""
    try:
        return storage.get_client()
    except KeyError:
        print("(R2 자격증명 없음 — 로컬에만 저장)")
        return None


def make_source() -> GameSource:
    cfg = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))["portal"]
    return PortalSource(cfg)


def raw_key(source: GameSource, ref: GameRef) -> str:
    """R2 키 = 로컬 경로에서 data/ 프리픽스만 뺀 것 (계획서 5장 레이아웃)."""
    return f"raw/source={source.source_name}/dt={ref.date}/game_{ref.game_id}.json"


def load_or_fetch_raw(source: GameSource, ref: GameRef, s3=None) -> tuple[dict, str]:
    """멱등 수집: R2 객체 존재가 진실의 원천 (계획서 7장 — 상태를 스토리지에서 유도).

    폴백 순서 (반환: (raw, 출처)):
      1. 로컬 파일 → 그대로 사용 (빠른 캐시)                     출처 "local"
      2. R2에 존재 → 다운로드해 사용 (소스 재요청 없음)           출처 "r2"
      3. 둘 다 없음 → 소스에서 수집, 로컬 저장 + R2 업로드        출처 "fetched"
    러너가 매번 초기화되는 환경(GitHub Actions)에서도 상태를 잃지 않는 근거.
    """
    raw_path = Path(f"data/raw/source={source.source_name}/dt={ref.date}") / f"game_{ref.game_id}.json"
    key = raw_key(source, ref)

    if raw_path.exists():
        return json.loads(raw_path.read_text(encoding="utf-8")), "local"

    if s3 is not None and storage.object_exists(s3, key):
        storage.download_file(s3, key, raw_path)
        return json.loads(raw_path.read_text(encoding="utf-8")), "r2"

    raw = source.fetch_raw(ref)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    if s3 is not None:
        storage.upload_file(s3, raw_path, key)
    return raw, "fetched"


_ORIGIN_LABEL = {"local": "로컬 캐시", "r2": "R2에서 복원", "fetched": "신규 수집→R2 업로드"}


def ingest_game(source: GameSource, ref: GameRef, s3=None) -> list[dict]:
    raw, origin = load_or_fetch_raw(source, ref, s3=s3)
    print(f"  {ref.game_id}: {_ORIGIN_LABEL[origin]}")
    rows = source.parse_pitches(raw, ref.game_id)
    assert_seq_contiguous(rows)
    return rows


def write_bronze(rows: list[dict], dt: str, s3=None) -> Path:
    df = pl.DataFrame(rows)
    bronze_dir = Path(f"data/bronze/dt={dt}")
    bronze_dir.mkdir(parents=True, exist_ok=True)
    out = bronze_dir / "pitches.parquet"
    df.write_parquet(out, compression="zstd")
    if s3 is not None:
        storage.upload_file(s3, out, f"bronze/dt={dt}/pitches.parquet")
        print(f"  R2 업로드 (bronze dt={dt})")
    return out


def main() -> None:
    source = make_source()
    mode = sys.argv[1]

    if mode == "--list":
        for ref in source.list_games(sys.argv[2]):
            mark = "O" if source.is_target(ref) else "X"
            print(f"[{mark}] {ref.game_id} {ref.category} {ref.away} vs {ref.home} | {ref.status}")
        return

    if mode == "--date":
        dt = sys.argv[2]
        s3 = get_s3_or_none()
        games = source.list_games(dt)
        targets = [ref for ref in games if source.is_target(ref)]
        print(f"{dt}: 전체 {len(games)}경기, 수집 대상(KBO·RESULT) {len(targets)}경기")
        all_rows: list[dict] = []
        for ref in targets:
            rows = ingest_game(source, ref, s3=s3)
            print(f"  {ref.game_id}: {len(rows)} pitches")
            if not rows:
                print(f"  경고: {ref.game_id} 투구 0건 — relay 구조 확인 필요")
            all_rows.extend(rows)
        if not all_rows:
            print("수집된 투구 없음")
            sys.exit(1)
        out = write_bronze(all_rows, dt, s3=s3)
        print(f"OK: {len(targets)} games, {len(all_rows)} pitches -> {out}")
        return

    # 기본: 경기 1개
    game_id, dt = mode, sys.argv[2]
    s3 = get_s3_or_none()
    rows = ingest_game(source, GameRef(game_id=game_id, date=dt), s3=s3)
    if not rows:
        print("파싱 결과 0행 — 응답 구조 확인 필요")
        sys.exit(1)
    out = write_bronze(rows, dt, s3=s3)
    print(f"OK: {len(rows)} pitches -> {out}")


if __name__ == "__main__":
    main()
