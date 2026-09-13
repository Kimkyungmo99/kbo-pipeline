"""피치클락 페널티 이벤트 테스트 — 2025-03-09 LGKT 1회초 오스틴 타석 실측 재현.

소스는 페널티를 "1구 피치클락 투수위반 볼"처럼 구 번호를 소비하는 텍스트 옵션으로 기록한다.
이를 버리면 다음 투구가 2-0에서 시작하는 것처럼 보여 전이 검증이 깨진다 (2025-03~04 위반 58건).
이벤트 행으로 보존하면 카운트 흐름이 이어지고, event_type으로 투구와 구분된다.
"""
from ingestion.parsers.portal import parse_pitches, pitch_clock_event


def pitch(pn, res, text, ball, strike):
    return {"pitchNum": pn, "pitchResult": res, "text": text,
            "currentGameState": {"ball": ball, "strike": strike, "out": 0, "batter": "B1"}}


def text_opt(text, ball=None, strike=None):
    opt = {"text": text}
    if ball is not None:
        opt["currentGameState"] = {"ball": ball, "strike": strike, "out": 0, "batter": "B1"}
    return opt


def raw_of(options):
    return {"result": {"textRelayData": {"textRelays": [
        {"no": 3, "inn": 1, "homeOrAway": "A", "textOptions": options},
    ]}}}


def test_pitch_clock_ball_preserved_as_event():
    raw = raw_of([
        text_opt("3번타자 오스틴"),
        text_opt("1구 피치클락 투수위반 볼", 1, 0),
        pitch(2, "B", "2구 볼", 2, 0),
        pitch(3, "T", "3구 스트라이크", 2, 1),
    ])
    rows = parse_pitches(raw, "20250309LGKT02025")
    assert [r["event_type"] for r in rows] == ["pitch_clock_ball", "pitch", "pitch"]
    assert [(r["balls"], r["strikes"]) for r in rows] == [(1, 0), (2, 0), (2, 1)]  # 카운트 흐름 연속
    assert [r["pitch_seq_in_game"] for r in rows] == [1, 2, 3]
    assert rows[0]["result"] is None and rows[0]["pitch_type"] is None  # 투구로 위장하지 않는다


def test_pitch_clock_strike_detected():
    assert pitch_clock_event(text_opt("2구 피치클락 타자위반 스트라이크", 0, 1)) == "pitch_clock_strike"


def test_2024_warning_is_not_an_event():
    # 2024는 경고제 — 카운트 변화 없음 → 이벤트 아님 (3,900건 실측 전부 '경고'로 끝남)
    assert pitch_clock_event(text_opt("6회말 3번타순 초구 전 피치클락 위반 타자 경고 : 두산 허경민", 0, 0)) is None
    assert pitch_clock_event(text_opt("1회초 1번타순 초구 전 외야 피치클락 고장으로 피치클락 운영하지 않음", 0, 1)) is None


def test_batter_announcement_without_state_is_ignored():
    assert pitch_clock_event(text_opt("3번타자 오스틴")) is None
