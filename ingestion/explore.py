"""엔드포인트 탐색 보조: 응답 구조를 눈으로 확인하고 최소 샘플을 저장한다.

사용:
    python -m ingestion.explore <YYYY-MM-DD>              # 경기 목록 + 첫 경기 relay 구조 출력
    python -m ingestion.explore <YYYY-MM-DD> --save       # docs/source-schema/ 에 트림된 샘플 저장
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ingestion.run import fetch_game, list_games, load_cfg
from ingestion.parsers.portal import extract_text_relays


def key_tree(obj, depth=0, max_depth=4) -> None:
    pad = "  " * depth
    if depth > max_depth:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            print(f"{pad}{k}: {type(v).__name__}")
            key_tree(v, depth + 1, max_depth)
    elif isinstance(obj, list) and obj:
        print(f"{pad}[{len(obj)}개] 첫 원소:")
        key_tree(obj[0], depth + 1, max_depth)


def main() -> None:
    date = sys.argv[1]
    save = "--save" in sys.argv
    cfg = load_cfg()

    games = list_games(date, cfg)
    print(f"== {date} 경기 {len(games)}개 ==")
    for g in games:
        print(" ", g.get("gameId"), g.get("awayTeamName"), "vs", g.get("homeTeamName"),
              "|", g.get("statusCode"))
    # 취소 경기는 relay가 null — 종료(RESULT) 경기만 대상으로 한다
    done = [g for g in games if g.get("statusCode") == "RESULT"]
    if not done:
        print("종료(RESULT) 경기가 없음 — 다른 날짜로 시도할 것")
        return

    game_id = done[0]["gameId"]
    print(f"\n== relay 구조 ({game_id}) ==")
    raw = fetch_game(game_id, cfg)
    key_tree(raw)

    relays = extract_text_relays(raw)
    print(f"\ntextRelays: {len(relays)}개")
    if relays:
        print("첫 타석 원본:")
        print(json.dumps(relays[0], ensure_ascii=False, indent=2)[:3000])

    if save and relays:
        out = Path("docs/source-schema")
        out.mkdir(parents=True, exist_ok=True)
        # 구조 파악용 최소 샘플: 타석 5개만 남긴다 (실데이터 커밋 최소화 원칙)
        sample = {"result": {"textRelayData": {"textRelays": relays[:5]}}}
        (out / "portal_pitch_sample.json").write_text(
            json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n저장: docs/source-schema/portal_pitch_sample.json (타석 {min(5, len(relays))}개)")


if __name__ == "__main__":
    main()
