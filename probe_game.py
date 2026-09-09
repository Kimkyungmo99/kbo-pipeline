"""전이 위반 경기 정밀 조사 — 위반 seq 주변을 (1) 파싱 결과, (2) raw 원본 두 관점에서 출력.

check_transitions가 플래그한 seq를 넣으면:
  [파싱 관점] 위반 seq 앞뒤 몇 행의 카운트·결과·텍스트 흐름
  [raw 관점]  그 seq가 속한 relay(타석)와 직전 relay의 원본 옵션 전부
              — pitchNum 누락(1,2,5,6…), 동일 pitchNum 중복, 타석 종료 텍스트가 그대로 보인다

사용: py probe_game.py <game_id> <YYYY-MM-DD> <seq> [<seq> ...]
예:   py probe_game.py 20240724WOOB02024 2024-07-24 187 211 277 313
"""
import json
import sys
from pathlib import Path

from ingestion.parsers.portal import (
    _options_of,
    extract_text_relays,
    is_pitch_option,
    parse_pitches,
)

game_id, date = sys.argv[1], sys.argv[2]
targets = [int(s) for s in sys.argv[3:]]

raw_path = Path(f"data/raw/source=portal/dt={date}/game_{game_id}.json")
raw = json.loads(raw_path.read_text(encoding="utf-8"))
rows = parse_pitches(raw, game_id)
relays = extract_text_relays(raw)

# seq → relay 인덱스 매핑 — relay 하나짜리 raw를 파서에 넣어 행 수를 세는 방식으로
# 파서 규칙(중복 제거·타석 합침 처리)을 그대로 재사용한다.
# (처음엔 dedup 규칙을 여기 복제했다가 파서가 바뀌자 매핑이 어긋났다 — 2026-09-10 교훈:
#  판정 로직은 한 곳에만 둔다)
seq_to_ri: dict[int, int] = {}
seq = 0
for ri, relay in enumerate(relays):
    n = len(parse_pitches({"result": {"textRelayData": {"textRelays": [relay]}}}, game_id))
    for s in range(seq + 1, seq + n + 1):
        seq_to_ri[s] = ri
    seq += n


def dump_relay(ri: int, label: str) -> None:
    relay = relays[ri]
    print(f"  --- {label}: relay no={relay.get('no')} | {relay.get('inn') or relay.get('inning')}회 "
          f"| batter={relay.get('batterCode') or relay.get('batter')} ---")
    for opt in _options_of(relay):
        if not isinstance(opt, dict):
            continue
        pn = opt.get("pitchNum")
        res = opt.get("pitchResult") or opt.get("result") or ""
        gs = opt.get("currentGameState") or {}
        cnt = f"B{gs.get('ball')}-S{gs.get('strike')}" if gs else "      "
        text = (opt.get("text") or opt.get("playText") or "").strip()
        kind = "투구" if is_pitch_option(opt) else "텍스트"
        print(f"    [{kind}] pitchNum={pn!s:>4} {res:>2} {cnt} | {text}")


for t in targets:
    print(f"\n{'=' * 70}\n■ seq {t}")
    print("  [파싱 관점] 위반 지점 앞뒤 흐름")
    for r in rows:
        if t - 3 <= r["pitch_seq_in_game"] <= t + 1:
            mark = " ←위반" if r["pitch_seq_in_game"] == t else ""
            print(f"    seq {r['pitch_seq_in_game']:>3} | {r['inning']}회{'초' if r['is_top'] else '말'} "
                  f"| B{r['balls']}-S{r['strikes']} O{r['outs']} | {r['result']} | {r['text']}{mark}")
    ri = seq_to_ri.get(t)
    if ri is None:
        print("  (seq 매핑 실패 — raw 구조 확인 필요)")
        continue
    print("  [raw 관점] 원본 기록 (중복·비투구 텍스트 포함, 원본 순서 그대로)")
    if ri > 0:
        dump_relay(ri - 1, "직전 relay")
    dump_relay(ri, "위반 seq가 속한 relay")
