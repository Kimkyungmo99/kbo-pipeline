"""파서 테스트 (D3) — 네트워크 없이 fixture만으로 돈다.

전제: `python -m ingestion.explore <날짜> --save` 로
docs/source-schema/portal_pitch_sample.json 이 생성돼 있어야 한다.
샘플 저장 후 아래 EXPECTED 값을 실제 값으로 채운다.
"""
import json
from pathlib import Path

import pytest

from ingestion.parsers.portal import assert_seq_contiguous, parse_pitches

SAMPLE = Path("docs/source-schema/portal_pitch_sample.json")


@pytest.fixture()
def raw():
    if not SAMPLE.exists():
        pytest.skip("샘플 없음 — ingestion.explore --save 먼저 실행")
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def test_rows_parsed(raw):
    rows = parse_pitches(raw, "TESTGAME")
    assert len(rows) > 0


def test_seq_is_contiguous_from_1(raw):
    rows = parse_pitches(raw, "TESTGAME")
    assert_seq_contiguous(rows)  # 통과해야 정상


def test_seq_assertion_catches_gap(raw):
    rows = parse_pitches(raw, "TESTGAME")
    rows[-1]["pitch_seq_in_game"] += 1  # 인위적 누락 — 어서션이 잡아야 한다
    with pytest.raises(AssertionError):
        assert_seq_contiguous(rows)


def test_ballcount_from_current_game_state(raw):
    """D2: currentGameState에서 볼카운트가 채워지는지 (전부 null이면 실패)."""
    rows = parse_pitches(raw, "TESTGAME")
    filled = [r for r in rows if r["balls"] is not None and r["strikes"] is not None]
    assert len(filled) > 0, "balls/strikes가 전부 null — currentGameState 파싱 확인 필요"
    # 느슨한 범위만 확인 (currentGameState가 투구 직후 상태면 볼4/스트라이크3이 나올 수 있음.
    # 엄격한 0~3/0~2 검증은 시점 확정 후 DuckDB 쿼리에서)
    for r in filled:
        assert 0 <= r["balls"] <= 4
        assert 0 <= r["strikes"] <= 3
