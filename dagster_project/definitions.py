"""Dagster 정의 — 얇은 래퍼만 둔다. 수집 로직은 전부 ingestion/ (Dagster 비의존).

실행:
    py -m dagster dev -f dagster_project/definitions.py
    → http://localhost:3000 → Assets → raw_pitch_events → Materialize (파티션 선택)
"""
import json
from pathlib import Path

from dagster import AssetExecutionContext, DailyPartitionsDefinition, Definitions, asset

from ingestion.parsers.portal import assert_seq_contiguous
from ingestion.run import get_s3_or_none, load_or_fetch_raw, make_source, write_bronze

# 파티션 = 경기 날짜 (계획서 7장). 백필 시작점 2024 시즌 개막 전.
kbo_daily = DailyPartitionsDefinition(
    start_date="2024-03-01",
    timezone="Asia/Seoul",
)


@asset(partitions_def=kbo_daily, group_name="ingestion")
def raw_pitch_events(context: AssetExecutionContext) -> None:
    """해당 날짜의 KBO·RESULT 경기 raw JSON을 적재한다.

    멱등: raw 파일 존재 여부로 스킵 판단 (계획서 7장 — 상태를 스토리지에서 유도).
    월요일 등 경기 없는 날은 0경기가 정상 — 실패로 처리하지 않는다.
    """
    dt = context.partition_key  # "YYYY-MM-DD"
    source = make_source()
    s3 = get_s3_or_none()

    games = source.list_games(dt)
    targets = [ref for ref in games if source.is_target(ref)]
    context.log.info(f"{dt}: 전체 {len(games)}경기, 수집 대상(KBO·RESULT) {len(targets)}경기")

    origins = {"local": 0, "r2": 0, "fetched": 0}
    pitch_count = 0
    for ref in targets:
        raw, origin = load_or_fetch_raw(source, ref, s3=s3)
        origins[origin] += 1
        context.log.info(f"{ref.game_id}: {origin}")
        pitch_count += len(source.parse_pitches(raw, ref.game_id))

    # 파티션별 행 수 추이가 "관측 가능한 파이프라인"의 증거 (계획서 7장)
    context.add_output_metadata({
        "game_count": len(games),
        "target_count": len(targets),
        "from_local": origins["local"],
        "from_r2": origins["r2"],
        "newly_fetched": origins["fetched"],
        "pitch_count": pitch_count,
    })


@asset(partitions_def=kbo_daily, group_name="ingestion", deps=[raw_pitch_events])
def bronze_pitches(context: AssetExecutionContext) -> None:
    """raw JSON → 타입 정리된 Parquet (bronze 레이어, 계획서 5장).

    raw 파일만 읽는다 — 네트워크 접근 없음 (재파싱 가능성이 raw 보존의 이유).
    경기 없는 날은 0행이 정상: Parquet을 쓰지 않고 성공 처리한다.
    """
    dt = context.partition_key
    source = make_source()
    raw_dir = Path(f"data/raw/source={source.source_name}/dt={dt}")

    all_rows: list[dict] = []
    game_count = 0
    for raw_path in sorted(raw_dir.glob("game_*.json")) if raw_dir.exists() else []:
        game_id = raw_path.stem.removeprefix("game_")
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        rows = source.parse_pitches(raw, game_id)
        assert_seq_contiguous(rows)  # 파싱 누락 탐지 (경기 단위)
        context.log.info(f"{game_id}: {len(rows)} pitches")
        game_count += 1
        all_rows.extend(rows)

    if not all_rows:
        context.log.info(f"{dt}: 투구 없음 (경기 없는 날 또는 raw 미수집) — 정상 처리")
        context.add_output_metadata({"game_count": 0, "pitch_count": 0})
        return

    out = write_bronze(all_rows, dt)
    context.add_output_metadata({
        "game_count": game_count,
        "pitch_count": len(all_rows),
        "path": str(out),
    })


defs = Definitions(assets=[raw_pitch_events, bronze_pitches])
