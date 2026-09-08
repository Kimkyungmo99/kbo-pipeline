"""수집 완전성 검증 — 목록 API의 KBO·RESULT 경기 수와 bronze의 경기 수를 일별 대조.

경기 수 범위 검사(check_sanity)로는 "부분 수집 실패"와 "우천으로 원래 적은 날"을
구분할 수 없다 (2024-06-29 실측: 취소 4 + RESULT 1의 합법적 1경기 날 존재).
이 검사는 목록 API를 진실의 원천으로 삼아 그 구분을 해낸다.

주의: 날짜당 목록 API 1회 요청 (1초 딜레이 포함) — 전체 실행 시 날짜 수 × ~1.5초.
사용:
    py check_completeness.py                       # bronze의 모든 날짜
    py check_completeness.py 2024-07-01 2024-07-31 # 범위 지정 (권장)
"""
import sys
from pathlib import Path

import polars as pl

from ingestion.run import make_source

source = make_source()

dts = sorted(
    p.name.removeprefix("dt=")
    for p in Path("data/bronze").iterdir()
    if p.is_dir() and p.name.startswith("dt=")
)
if len(sys.argv) == 3:
    dts = [d for d in dts if sys.argv[1] <= d <= sys.argv[2]]

print(f"{len(dts)}개 날짜 대조 (예상 소요 ~{int(len(dts) * 1.5)}초)")
mismatch = 0
for dt in dts:
    df = pl.read_parquet(f"data/bronze/dt={dt}/pitches.parquet", columns=["game_id"])
    have = df["game_id"].n_unique()
    expected = sum(1 for r in source.list_games(dt) if source.is_target(r))
    ok = have == expected
    if not ok:
        mismatch += 1
    flag = "" if ok else "  ← 불일치! (수집 누락 또는 소스 변동)"
    print(f"  {dt}: bronze {have}경기 / 목록 RESULT {expected}경기{flag}")

print(f"\n{'완전성 통과 — 전 날짜 일치' if mismatch == 0 else f'불일치 {mismatch}일 — 해당 날짜 재수집 권장 (멱등이라 --date 재실행이면 됨)'}")
