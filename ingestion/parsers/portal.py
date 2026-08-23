"""네이버 스포츠 문자중계(relay) JSON → 투구 단위 행 파서.

순수 함수만 둔다 — 네트워크·파일 IO 금지 (fetch와 분리, D3 테스트 대상).

관찰된 구조 (비공식, 변경 가능):
  relay 응답 = {"success": true, "result": {"textRelayData": {...}}}
  textRelayData.textRelays  = 타석/이벤트 단위 리스트
  각 textRelay.textOptions (또는 options) = 투구/텍스트 옵션 리스트
    투구 옵션: {"pitchNum": 1, "speed": "145", "stuff": "직구",
               "pitchResult": "B"|"S"|"F"|"H"..., "text": "...", ...}
실제 키 이름은 탐색 후 이 파일만 고치면 된다.
"""
from __future__ import annotations

from typing import Any

# 투구 옵션에서 뽑을 필드 후보 (왼쪽부터 시도)
_FIELD_CANDIDATES = {
    "pitch_type": ("stuff", "pitchType", "stuffName"),
    "velocity": ("speed", "pitchSpeed"),
    "result": ("pitchResult", "result"),
    "text": ("text", "playText"),
    "balls": ("ballCount", "balls", "b"),
    "strikes": ("strikeCount", "strikes", "s"),
    "outs": ("outCount", "outs", "o"),
}


def _first(d: dict, keys: tuple[str, ...], default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def _to_float(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def extract_text_relays(raw: dict) -> list[dict]:
    """relay 응답(이닝별 응답 리스트 병합본 포함)에서 textRelay 리스트를 꺼낸다.

    소스는 웹 표시 순서(최신이 먼저 = `no` 내림차순)로 주므로,
    시간순 seq 부여를 위해 `no` 오름차순으로 정렬해 반환한다.
    (볼카운트 전이 검증이 잡아낸 버그 — 2026-08-24)
    """
    result = raw.get("result", raw)
    data = result.get("textRelayData") or result.get("textRelay") or {}
    if isinstance(data, list):  # 이닝별 리스트로 오는 경우
        relays: list[dict] = []
        for chunk in data:
            relays.extend(chunk.get("textRelays", []))
    else:
        relays = list(data.get("textRelays", []))
    # no가 없는 relay는 뒤로, 나머지는 시간순(오름차순)
    relays.sort(key=lambda r: (r.get("no") is None, r.get("no") or 0))
    return relays


def _options_of(relay: dict) -> list[dict]:
    return relay.get("textOptions") or relay.get("options") or []


def is_pitch_option(opt: dict) -> bool:
    """투구가 아닌 텍스트(교체·안내 등) 옵션을 걸러낸다."""
    return _to_int(opt.get("pitchNum")) is not None or _first(opt, _FIELD_CANDIDATES["result"]) is not None


def parse_pitches(raw: dict, game_id: str) -> list[dict[str, Any]]:
    """경기 relay JSON → 투구 단위 행 리스트.

    볼카운트·아웃·주루·점수는 옵션 안의 `currentGameState`에서 읽는다 (D1에서 확인).
    주의: currentGameState가 투구 '직전'인지 '직후' 상태인지는 아직 미검증 —
    볼카운트 전이 검증(계획서 8장) 구현 시 확정한다.
    """
    rows: list[dict[str, Any]] = []
    seq = 0
    for relay in extract_text_relays(raw):
        inning = _to_int(_first(relay, ("inn", "inning")))
        is_top = relay.get("homeOrAway") in ("A", "away", 0, "0") or relay.get("btop")
        batter = _first(relay, ("batterCode", "batter", "batterName"))
        pitcher = _first(relay, ("pitcherCode", "pitcher", "pitcherName"))
        for opt in _options_of(relay):
            if not isinstance(opt, dict) or not is_pitch_option(opt):
                continue
            seq += 1
            gs = opt.get("currentGameState") or {}
            pitcher_id = gs.get("pitcher") or pitcher
            batter_id = gs.get("batter") or batter
            rows.append({
                "game_id": game_id,
                "pitch_seq_in_game": seq,
                "inning": inning,
                "is_top": bool(is_top) if is_top is not None else None,
                "pitcher_id": str(pitcher_id) if pitcher_id is not None else None,
                "batter_id": str(batter_id) if batter_id is not None else None,
                "balls": _to_int(gs.get("ball")) if gs else _to_int(_first(opt, _FIELD_CANDIDATES["balls"])),
                "strikes": _to_int(gs.get("strike")) if gs else _to_int(_first(opt, _FIELD_CANDIDATES["strikes"])),
                "outs": _to_int(gs.get("out")) if gs else _to_int(_first(opt, _FIELD_CANDIDATES["outs"])),
                "base1": _to_int(gs.get("base1")),
                "base2": _to_int(gs.get("base2")),
                "base3": _to_int(gs.get("base3")),
                "score_home": _to_int(gs.get("homeScore")),
                "score_away": _to_int(gs.get("awayScore")),
                "pitch_type": _first(opt, _FIELD_CANDIDATES["pitch_type"]),
                "velocity": _to_float(_first(opt, _FIELD_CANDIDATES["velocity"])),
                "result": _first(opt, _FIELD_CANDIDATES["result"]),
                "text": _first(opt, _FIELD_CANDIDATES["text"]),
            })
    return rows


def assert_seq_contiguous(rows: list[dict[str, Any]]) -> None:
    """pitch_seq_in_game이 1부터 빈틈없이 연속인지 — 파싱 누락 탐지 장치 (계획서 5장)."""
    seqs = [r["pitch_seq_in_game"] for r in rows]
    expected = list(range(1, len(rows) + 1))
    assert seqs == expected, (
        f"seq 연속성 위반: 총 {len(rows)}행인데 seq가 1..{len(rows)}과 불일치 — 파싱 누락 의심"
    )
