"""Dagster 정의 — 얇은 래퍼만 둔다. 수집 로직은 전부 ingestion/ (Dagster 비의존).

실행:
    py -m dagster dev -f dagster_project/definitions.py
    → http://localhost:3000 → Assets → raw_pitch_events → Materialize (파티션 선택)
"""
import json
from pathlib import Path

from dagster import AssetExecutionContext, DailyPartitionsDefinition, Definitions, asset

from ingestion.run import make_source

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

    games = source.list_games(dt)
    targets = [ref for ref in games if source.is_target(ref)]
    context.log.info(f"{dt}: 전체 {len(games)}경기, 수집 대상(KBO·RESULT) {len(targets)}경기")

    new_count = 0
    pitch_count = 0
    for ref in targets:
        raw_dir = Path(f"data/raw/source={source.source_name}/dt={ref.date}")
        raw_path = raw_dir / f"game_{ref.game_id}.json"
        if raw_path.exists():
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            context.log.info(f"{ref.game_id}: 이미 적재됨 — 스킵 (멱등)")
        else:
            raw = source.fetch_raw(ref)
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            new_count += 1
            context.log.info(f"{ref.game_id}: 신규 수집")
        pitch_count += len(source.parse_pitches(raw, ref.game_id))

    # 파티션별 행 수 추이가 "관측 가능한 파이프라인"의 증거 (계획서 7장)
    context.add_output_metadata({
        "game_count": len(games),
        "target_count": len(targets),
        "new_game_count": new_count,
        "pitch_count": pitch_count,
    })


defs = Definitions(assets=[raw_pitch_events])
