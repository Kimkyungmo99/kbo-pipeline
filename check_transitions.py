"""볼카운트 전이 검증 초안 (계획서 8장, ADR 002 후보).

규칙 (우리 데이터는 '투구 직후' 상태임을 반영):
- 타석 안에서 카운트는 감소하지 않는다 → 감소가 보이면 새 타석 시작으로 판정
- 타석 내 전이는 셋 중 하나만 합법:
    볼+1        (Δb,Δs) = (1,0)
    스트라이크+1 (Δb,Δs) = (0,1)   (s<3까지)
    변화 없음    (Δb,Δs) = (0,0)   (2스트라이크 파울, 또는 인플레이)
- 새 타석의 첫 상태는 (0,0)·(0,1)·(1,0) 중 하나여야 한다
  ((0,0)은 초구 인플레이 — 카운트 변화 없이 타석 종료)

이 규칙을 벗어나는 전이 = 파싱 누락(투구 빠짐) 또는 소스 오류 후보.
"""
import polars as pl

P = "data/bronze/dt=*/pitches.parquet"

df = pl.read_parquet(P).sort(["game_id", "pitch_seq_in_game"])

legal_within = 0
pa_starts_ok = 0
violations: list[dict] = []
transition_counts: dict[tuple, int] = {}

prev = None  # (game_id, balls, strikes)
for row in df.iter_rows(named=True):
    cur = (row["balls"], row["strikes"])
    if prev is None or prev[0] != row["game_id"]:
        kind = "게임 첫 투구"
        ok = cur in {(0, 0), (0, 1), (1, 0)}
        pa_starts_ok += ok
    else:
        db, ds = cur[0] - prev[1], cur[1] - prev[2]
        transition_counts[(db, ds)] = transition_counts.get((db, ds), 0) + 1
        if db < 0 or ds < 0:
            kind = "새 타석 시작(카운트 감소)"
            ok = cur in {(0, 0), (0, 1), (1, 0)}
            pa_starts_ok += ok
        else:
            kind = "타석 내 전이"
            ok = (db, ds) in {(1, 0), (0, 1), (0, 0)} and cur[1] <= 3 and cur[0] <= 4
            legal_within += ok
    if not ok:
        violations.append({
            "game_id": row["game_id"], "seq": row["pitch_seq_in_game"],
            "종류": kind, "카운트": f"{cur[0]}-{cur[1]}",
            "result": row["result"], "text": row["text"],
        })
    prev = (row["game_id"], cur[0], cur[1])

print(f"총 {len(df)}투구")
print(f"타석 내 합법 전이: {legal_within} / 타석 시작 정상: {pa_starts_ok}")
print(f"\n전이 분포 (Δ볼, Δ스트라이크) — 음수는 새 타석:")
for (db, ds), n in sorted(transition_counts.items(), key=lambda x: -x[1]):
    print(f"  ({db:+d},{ds:+d}): {n}")

print(f"\n불법 전이: {len(violations)}건")
for v in violations[:10]:
    print(" ", v)
if len(violations) > 10:
    print(f"  ... 외 {len(violations)-10}건")
