"""파서 중복 제거 vs 타석 합침 구분 테스트 (2024-07-24 WOOB 실측 재현).

소스는 ① 같은 투구를 같은 내용으로 두 번 기록하기도 하고(진짜 중복),
② 두 타석을 relay 하나에 합쳐 pitchNum이 1부터 재시작하기도 한다(타석 합침).
①만 제거하고 ②는 보존해야 한다 — 구버전 dedup은 ②에서 실제 투구를 삭제했다.
"""
from ingestion.parsers.portal import parse_pitches


def opt(pn, res, text, batter, ball, strike):
    return {
        "pitchNum": pn, "pitchResult": res, "text": text,
        "currentGameState": {"ball": ball, "strike": strike, "out": 0, "batter": batter},
    }


def raw_of(options):
    return {"result": {"textRelayData": {"textRelays": [
        {"no": 1, "inn": 1, "homeOrAway": "A", "textOptions": options},
    ]}}}


def test_true_duplicate_removed():
    # 2024-07-24 7회초 실측: 8구 타격이 같은 내용으로 두 번 기록됨
    raw = raw_of([
        opt(1, "T", "1구 스트라이크", "B1", 0, 1),
        opt(2, "H", "2구 타격", "B1", 0, 1),
        opt(2, "H", "2구 타격", "B1", 0, 1),  # 동일 번호+내용+타자 → 중복
    ])
    rows = parse_pitches(raw, "TEST")
    assert len(rows) == 2
    assert [r["text"] for r in rows] == ["1구 스트라이크", "2구 타격"]


def test_merged_plate_appearance_preserved():
    # 2024-07-24 6회말 실측: 양의지 타석 뒤에 양석환 타석이 같은 relay에 합쳐짐
    raw = raw_of([
        opt(1, "T", "1구 스트라이크", "B1", 0, 1),
        opt(2, "H", "2구 타격", "B1", 0, 1),
        opt(1, "S", "1구 헛스윙", "B2", 0, 1),  # 번호 역행 + 다른 타자 = 새 타석
        opt(2, "B", "2구 볼", "B2", 1, 1),
    ])
    rows = parse_pitches(raw, "TEST")
    assert len(rows) == 4  # 구버전 dedup은 뒤 2개를 삭제했다
    assert [r["batter_id"] for r in rows] == ["B1", "B1", "B2", "B2"]
    assert [r["pitch_seq_in_game"] for r in rows] == [1, 2, 3, 4]
