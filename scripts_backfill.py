"""월 단위 백필 드라이버 — 엄격한 순차 실행 (수집 예의: 동시 요청 없음, 1초 딜레이 준수).

Dagster UI backfill 대신 이 드라이버를 쓰는 이유:
UI backfill은 파티션 run을 동시에 띄울 수 있어 레이트리밋 원칙과 충돌한다.
수집은 여기서 순차로, Dagster 파티션 등록은 수집 후 UI에서 (전량 캐시 스킵이라 안전).

사용: py scripts_backfill.py 2024-04-01 2024-04-30
멱등: 중단돼도 같은 명령 재실행이면 이어서 진행 (이미 받은 경기는 스킵).
"""
import sys
import time
from datetime import date, timedelta

from ingestion.run import get_s3_or_none, ingest_game, make_source, write_bronze

start = date.fromisoformat(sys.argv[1])
end = date.fromisoformat(sys.argv[2])

source = make_source()
s3 = get_s3_or_none()

t0 = time.time()
total_games = total_pitches = empty_days = 0

d = start
while d <= end:
    dt = d.isoformat()
    try:
        games = source.list_games(dt)
        targets = [r for r in games if source.is_target(r)]
        day_rows: list[dict] = []
        for ref in targets:
            day_rows.extend(ingest_game(source, ref, s3=s3))
        if day_rows:
            write_bronze(day_rows, dt, s3=s3)
            total_games += len(targets)
            total_pitches += len(day_rows)
        else:
            empty_days += 1
        elapsed = int(time.time() - t0)
        print(f"[{dt}] {len(targets)}경기 {len(day_rows)}투구 | 누적 {total_games}경기 "
              f"{total_pitches}투구 | 경과 {elapsed//60}분{elapsed%60}초")
    except Exception as e:  # 하루 실패가 전체를 멈추지 않게 — 기록 후 계속
        print(f"[{dt}] 오류: {e} — 이 날짜는 건너뜀 (재실행 시 멱등 재시도됨)")
    d += timedelta(days=1)

print(f"\n백필 완료: {(end - start).days + 1}일 중 경기일 {(end - start).days + 1 - empty_days}일, "
      f"{total_games}경기 {total_pitches}투구, 총 {int(time.time()-t0)//60}분 소요")
