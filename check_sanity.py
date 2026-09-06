"""새니티 어서션 (계획서 8장 '기타 어서션').

1. 경기당 투구 수 100~500 — 벗어나면 수집 누락(이닝 빠짐) 또는 중복 병합 의심
2. 일별 경기 수 0 또는 2~10 — 1경기만 있는 날은 수집 실패 의심
   (정상: 월요일 0, 평일 5, 더블헤더 몰린 날 최대 10. 2024-04-21 실측: DH 3쌍 포함 8경기)
"""
import polars as pl

P = "data/bronze/dt=*/pitches.parquet"
df = pl.read_parquet(P, include_file_paths="path").with_columns(
    pl.col("path").str.extract(r"dt=(\d{4}-\d{2}-\d{2})").alias("dt")
)

fail = 0

print("== 1. 경기당 투구 수 (정상 100~500) ==")
per_game = df.group_by("dt", "game_id").len().sort("dt", "game_id")
for r in per_game.iter_rows(named=True):
    flag = "" if 100 <= r["len"] <= 500 else "  ← 범위 밖!"
    if flag:
        fail += 1
    print(f"  {r['dt']} {r['game_id']}: {r['len']}투구{flag}")

print("\n== 2. 일별 경기 수 (정상 0 또는 2~10, 더블헤더 포함) ==")
per_day = per_game.group_by("dt").len().sort("dt")
for r in per_day.iter_rows(named=True):
    ok = r["len"] == 0 or 2 <= r["len"] <= 10
    flag = "" if ok else "  ← 의심!"
    if flag:
        fail += 1
    print(f"  {r['dt']}: {r['len']}경기{flag}")

print(f"\n{'문제 없음 — 새니티 통과' if fail == 0 else f'경고 {fail}건 — 위 항목 확인 필요'}")
