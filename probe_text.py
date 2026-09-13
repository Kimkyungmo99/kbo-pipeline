"""raw 전체에서 텍스트 옵션 키워드 검색 — 비투구 이벤트(피치클락 위반 등)의 표기·빈도·형태 확인.

전이 검증은 bronze(투구 행)만 보므로, 투구가 아닌 옵션으로 기록된 이벤트(예: 자동 볼/스트라이크)는
bronze에 없다 — 그 존재를 raw에서 직접 세는 도구. 로컬 파일만 읽음 (소스 요청 0회).

사용: py probe_text.py <키워드> [dt 접두]
예:   py probe_text.py 피치클락 2025     # 2025 시즌 raw에서 '피치클락' 포함 옵션
      py probe_text.py 피치클락 2024     # 2024와 비교 (경고만 있어야 함)
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from ingestion.parsers.portal import _options_of, extract_text_relays, is_pitch_option

kw = sys.argv[1]
pref = sys.argv[2] if len(sys.argv) > 2 else ""

pattern_counts: Counter = Counter()
pattern_games: dict[str, set] = {}
examples: dict[str, dict] = {}
files = 0

for p in sorted(Path("data/raw/source=portal").glob(f"dt={pref}*/game_*.json")):
    files += 1
    raw = json.loads(p.read_text(encoding="utf-8"))
    gid = p.stem.removeprefix("game_")
    for relay in extract_text_relays(raw):
        for opt in _options_of(relay):
            if not isinstance(opt, dict):
                continue
            text = opt.get("text") or opt.get("playText") or ""
            if kw not in text:
                continue
            # 패턴화: 이름 부분(":" 뒤)과 숫자를 지워 같은 종류끼리 묶는다
            pat = re.sub(r"\d+", "N", text.split(":")[0]).strip()
            kind = "투구옵션" if is_pitch_option(opt) else "텍스트옵션"
            key = f"[{kind}] {pat}"
            pattern_counts[key] += 1
            pattern_games.setdefault(key, set()).add(gid)
            if key not in examples:
                gs = opt.get("currentGameState") or {}
                examples[key] = {
                    "game": gid, "relay_no": relay.get("no"), "text": text,
                    "pitchNum": opt.get("pitchNum"), "pitchResult": opt.get("pitchResult"),
                    "count_after": f"B{gs.get('ball')}-S{gs.get('strike')}" if gs else None,
                }

print(f"'{kw}' - raw {files}경기 파일 검색, 패턴 {len(pattern_counts)}종\n")
for key, n in pattern_counts.most_common():
    print(f"{n:>5}건 / {len(pattern_games[key]):>3}경기  {key}")
    print(f"        예: {examples[key]}")
