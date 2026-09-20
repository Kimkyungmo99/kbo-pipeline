"""GitHub Actions용 일일 수집기.

인자 없이 실행하면 한국 시간 기준 전날을 처리한다. 경기가 없던 날은 정상 종료하고,
완료 경기의 파싱 결과가 비어 있으면 실패한다.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ingestion.run import get_s3_or_none, ingest_game, make_source, report_skipped, write_bronze


def previous_kst_date() -> str:
    return (datetime.now(ZoneInfo("Asia/Seoul")) - timedelta(days=1)).date().isoformat()


def main() -> None:
    dt = sys.argv[1] if len(sys.argv) > 1 else previous_kst_date()
    source = make_source()
    games = source.list_games(dt)
    targets = [ref for ref in games if source.is_target(ref)]

    print(f"{dt}: 전체 {len(games)}경기, 완료된 수집 대상 {len(targets)}경기")
    report_skipped(source, games)
    if not targets:
        print("완료된 경기가 없어 정상 종료")
        return

    s3 = get_s3_or_none()
    if s3 is None:
        raise RuntimeError("일일 자동 수집에는 R2 자격증명이 필요합니다")

    all_rows: list[dict] = []
    for ref in targets:
        rows = ingest_game(source, ref, s3=s3)
        if not rows:
            raise RuntimeError(f"{ref.game_id}: 완료 경기의 파싱 결과가 0행입니다")
        print(f"  {ref.game_id}: {len(rows)} events")
        all_rows.extend(rows)

    out = write_bronze(all_rows, dt, s3=s3)
    print(f"OK: {len(targets)} games, {len(all_rows)} events -> {out}")


if __name__ == "__main__":
    main()
