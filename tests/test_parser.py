"""파서 테스트 (D3) — 네트워크 없이 fixture만으로 돈다.

전제: `python -m ingestion.explore <날짜> --save` 로
docs/source-schema/portal_pitch_sample.json 이 생성돼 있어야 한다.
샘플 저장 후 아래 EXPECTED 값을 실제 값으로 채운다.
"""
import json
from pathlib import Path

import pytest

from ingestion.parsers.portal import parse_pitches

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
    seqs = [r["pitch_seq_in_game"] for r in rows]
    assert seqs == list(range(1, len(rows) + 1))
