"""gameId 접두 → 경기 종류 분류 테스트. 접두 값은 전부 probe_list.py 실측 (2026-09-10~11)."""
import pytest

from ingestion.gametype import TARGET_GAME_TYPES, classify_game_type


@pytest.mark.parametrize("game_id, expected", [
    ("20240928HTLT02024", "regular"),
    ("20240421KTLT12024", "regular"),     # 더블헤더 1차전 — 경기번호 자리만 다름
    ("20250308HTLT02025", "exhibition"),  # 2025 시범경기 (개막 3/22 이전) — 목록 객체가 정규와 완전히 동일
    ("20250322HHKT02025", "regular"),     # 2025 개막전 — 경계값 (개막일 당일 = 정규)
    ("20240309HTLT02024", "exhibition"),  # 2024 시범경기 (개막 3/23)
    ("20260328LGKT02026", "regular"),     # 2026 개막일 (3/28, WBC로 늦은 개막)
    ("20270325LGKT02027", "unknown"),     # 개막일 미등록 시즌 → unknown (조용히 regular로 두지 않음)
    ("66661001SKKT02024", "tiebreaker"),  # 2024-10-01 5위 결정전
    ("44441002KTOB02024", "wildcard"),    # 2024-10-02 WC 1차전
    ("33331005KTLG02024", "semi_po"),     # 2024-10-05 준PO 1차전
    ("55551013LGSS02024", "po"),          # 2024-10-13 PO 1차전
    ("77771022SSHT02024", "ks"),          # 2024-10-22 KS 1차전 (우천 취소 상태였지만 접두는 확정)
    ("99990706WEEA02024", "allstar"),     # 2024-07-06 올스타전
    ("88881022HTSS02024", "unknown"),     # 미등록 접두는 unknown (8888은 날짜로도 파싱되지만 시즌과 불일치)
    ("20241002BL1", "unknown"),           # kbaseballetc 이벤트 — 형식 자체가 다름 (categoryId 필터도 막음)
])
def test_classify(game_id, expected):
    assert classify_game_type(game_id) == expected


def test_allstar_and_unknown_are_not_targets():
    assert "allstar" not in TARGET_GAME_TYPES
    assert "unknown" not in TARGET_GAME_TYPES


def test_postseason_types_are_targets():
    assert {"wildcard", "semi_po", "po", "ks", "tiebreaker"} <= TARGET_GAME_TYPES
