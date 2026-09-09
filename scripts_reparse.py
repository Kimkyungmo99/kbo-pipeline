"""로컬 raw 전체 재파싱 → bronze 재생성 + R2 업로드. 소스 요청 0회 (raw는 불변 원본).

파서가 바뀔 때 쓰는 도구 — "원본을 보존하면 파싱 로직의 모든 실수가 복구 가능"(Q1)의 실전 근거.
bronze 디렉터리가 있는 날짜만 대상 (걷어낸 날짜 — 예: 올스타전만 있던 2024-07-06 — 는 건드리지 않음).

사용: py scripts_reparse.py
"""
import json
import time
from pathlib import Path

from ingestion.parsers.portal import assert_seq_contiguous
from ingestion.run import get_s3_or_none, make_source, write_bronze

source = make_source()
s3 = get_s3_or_none()
t0 = time.time()
games = 0
total = 0

dts = sorted(
    p.name.removeprefix("dt=")
    for p in Path("data/bronze").iterdir()
    if p.is_dir() and p.name.startswith("dt=")
)
print(f"{len(dts)}개 날짜 재파싱 시작")
for dt in dts:
    all_rows: list[dict] = []
    for rp in sorted(Path(f"data/raw/source={source.source_name}/dt={dt}").glob("game_*.json")):
        game_id = rp.stem.removeprefix("game_")
        raw = json.loads(rp.read_text(encoding="utf-8"))
        rows = source.parse_pitches(raw, game_id)
        assert_seq_contiguous(rows)
        all_rows.extend(rows)
        games += 1
    write_bronze(all_rows, dt, s3=s3)
    total += len(all_rows)
    print(f"[{dt}] {len(all_rows)}투구 재생성")

print(f"\n재파싱 완료: {games}경기 {total}투구, {int(time.time() - t0)}초")
