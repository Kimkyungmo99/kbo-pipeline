"""목록 API 경기 객체의 필드 전수 출력 — 포스트시즌 식별 필드 찾기용 (날짜당 요청 1회).

사용:
    py probe_list.py 2024-09-28   # 정규시즌 표본
    py probe_list.py 2024-10-02   # 2024 와일드카드 1차전 (포스트시즌 표본)
    py probe_list.py 2024-10-01   # 정규/포스트 경계 확인
"""
import json
import sys

from ingestion.run import make_source

source = make_source()
date = sys.argv[1]
raw = source._get_json(source.cfg["game_list_url"].format(date=date))
games = raw.get("result", {}).get("games", [])
print(f"{date}: {len(games)}경기\n")
for g in games:
    scalars = {k: v for k, v in g.items() if not isinstance(v, (dict, list))}
    nested = [k for k, v in g.items() if isinstance(v, (dict, list))]
    print(json.dumps(scalars, ensure_ascii=False, indent=1))
    if nested:
        print(f"  (중첩 필드: {', '.join(nested)})")
    print("-" * 60)
