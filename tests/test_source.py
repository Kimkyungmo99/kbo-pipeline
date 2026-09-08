"""수집 대상 판별(is_target) 테스트 — 네트워크 불필요 (D3 원칙).

세 조건 각각을 실측 사례로 고정한다:
  category  — 비KBO는 RESULT여도 투구 relay 없음
  status    — 취소 경기는 relay null (2026-08-17 실측)
  gameId    — 올스타전은 categoryId=="kbo"인데 gameId가 9999로 시작 (2024-07-06 실측)
"""
from ingestion.base import GameRef
from ingestion.portal import PortalSource

SRC = PortalSource(cfg={})


def ref(game_id: str, date: str, category: str = "kbo", status: str = "RESULT") -> GameRef:
    return GameRef(game_id=game_id, date=date, category=category, status=status)


def test_regular_finished_game_is_target():
    assert SRC.is_target(ref("20240724WOOB02024", "2024-07-24"))


def test_allstar_game_excluded_by_gameid_date_prefix():
    # categoryId=="kbo" + RESULT라서 기존 두 조건은 통과하던 실측 케이스
    assert not SRC.is_target(ref("99990706WEEA02024", "2024-07-06"))


def test_cancelled_game_excluded():
    assert not SRC.is_target(ref("20240629OBLT02024", "2024-06-29", status="CANCEL"))


def test_non_kbo_game_excluded():
    assert not SRC.is_target(ref("20240724XXYY02024", "2024-07-24", category="mlb"))


def test_doubleheader_game_number_still_target():
    # 더블헤더는 경기번호 자리만 1/2 — 날짜 접두는 그대로라 계속 대상 (2024-04-21 실측)
    assert SRC.is_target(ref("20240421KTLT12024", "2024-04-21"))
