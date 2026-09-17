"""볼카운트 전이 검증 초안 (계획서 8장, ADR 002 후보).

규칙 (우리 데이터는 '투구 직후' 상태임을 반영):
- 이닝·공수·타자·카운트 리셋으로 새 타석을 판정한다. 대타가 나와도 카운트가 이어지면 같은 타석이다.
- 타석 내 전이는 셋 중 하나만 합법:
    볼+1        (Δb,Δs) = (1,0)
    스트라이크+1 (Δb,Δs) = (0,1)   (s<3까지)
    변화 없음    (Δb,Δs) = (0,0)   (2스트라이크 파울, 또는 인플레이)
- 새 타석의 첫 상태는 (0,0)·(0,1)·(1,0) 중 하나여야 한다
  ((0,0)은 초구 인플레이 — 카운트 변화 없이 타석 종료)

이 규칙을 벗어나는 전이 = 파싱 누락(투구 빠짐) 또는 소스 오류 후보.

사용: py check_transitions.py [--all]   # --all: 위반 전체 목록 (기본은 앞 10건)
"""
import sys
from collections import Counter

import polars as pl

P = "data/bronze/dt=*/pitches.parquet"
SHOW_ALL = "--all" in sys.argv

df = pl.read_parquet(P).sort(["game_id", "pitch_seq_in_game"])

legal_within = 0
pa_starts_ok = 0
violations: list[dict] = []
transition_counts: dict[tuple, int] = {}

prev = None  # 이전 이벤트 행
for row in df.iter_rows(named=True):
    cur = (row["balls"], row["strikes"])
    is_pa_start = (
        prev is None
        or prev["game_id"] != row["game_id"]
        or prev["inning"] != row["inning"]
        or prev["is_top"] != row["is_top"]
        or (
            prev["batter_id"] != row["batter_id"]
            and "대타" not in (prev.get("following_text") or "")
        )
        or row["balls"] < prev["balls"]
        or row["strikes"] < prev["strikes"]
    )
    if is_pa_start:
        kind = "새 타석 시작"
        ok = cur in {(0, 0), (0, 1), (1, 0)}
        pa_starts_ok += ok
    else:
        db, ds = cur[0] - prev["balls"], cur[1] - prev["strikes"]
        transition_counts[(db, ds)] = transition_counts.get((db, ds), 0) + 1
        kind = "타석 내 전이"
        ok = (db, ds) in {(1, 0), (0, 1), (0, 0)} and cur[1] <= 3 and cur[0] <= 4
        legal_within += ok
    if not ok:
        violations.append({
            "game_id": row["game_id"], "seq": row["pitch_seq_in_game"],
            "종류": kind, "카운트": f"{cur[0]}-{cur[1]}",
            "result": row["result"], "text": row["text"],
        })
    prev = row

print(f"총 {len(df)}투구")
print(f"타석 내 합법 전이: {legal_within} / 타석 시작 정상: {pa_starts_ok}")
print(f"\n타석 내 전이 분포 (Δ볼, Δ스트라이크):")
for (db, ds), n in sorted(transition_counts.items(), key=lambda x: -x[1]):
    print(f"  ({db:+d},{ds:+d}): {n}")

print(f"\n불법 전이: {len(violations)}건")

# 시즌별 요약 — 시즌 간 빈도 변화는 소스 형식 변화의 신호 (2025-03 실측: 10 → 38건)
pitches_by_season = Counter(g[-4:] for g in df["game_id"])
games_by_season = Counter(g[-4:] for g in df["game_id"].unique())
viol_by_season = Counter(v["game_id"][-4:] for v in violations)
print("  시즌별: " + " | ".join(
    f"{s}: {viol_by_season[s]}건 / {games_by_season[s]}경기 ({viol_by_season[s] / max(games_by_season[s], 1):.3f}건/경기)"
    for s in sorted(games_by_season)))
kind_counts = Counter((v["game_id"][-4:], v["종류"]) for v in violations)
for (s, k), n in sorted(kind_counts.items()):
    print(f"    {s} {k}: {n}")

shown = violations if SHOW_ALL else violations[:10]
for v in shown:
    print(" ", v)
if not SHOW_ALL and len(violations) > 10:
    print(f"  ... 외 {len(violations)-10}건 (--all 로 전체)")
