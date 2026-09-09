"""수집 대상 판별(is_target) 테스트 — 네트워크 불필요 (D3 원칙).

조건 셋을 실측 사례로 고정한다:
  category  — 비KBO는 RESULT여도 투구 relay 없음
  status    — 취소 경기는 relay null (2026-08-17 실측)
  종류      — gameId 접두로 판별: 올스타(9999)·미확인 접두 제외, 포스트시즌·순위결정전 포함
             (2024-07-06 올스타 사고 → 2026-09-10 포스트시즌 결정으로 규칙 교체)
"""
from ingestion.base import GameRef
from ingestion.portal import PortalSource

SRC = PortalSource(cfg={})


def ref(game_id: str, date: str, category: str = "kbo", status: str = "RESULT") -> GameRef:
    return GameRef(game_id=game_id, date=date, category=category, status=status)


def test_regular_finished_game_is_target():
    assert SRC.is_target(ref("20240724WOOB02024", "2024-07-24"))


def test_doubleheader_game_number_still_target():
    assert SRC.is_target(ref("20240421KTLT12024", "2024-04-21"))


def test_allstar_excluded():
    # categoryId=="kbo" + RESULT라서 앞 두 조건은 통과하던 실측 케이스
    assert not SRC.is_target(ref("99990706WEEA02024", "2024-07-06"))


def test_postseason_and_tiebreaker_included():
    assert SRC.is_target(ref("66661001SKKT02024", "2024-10-01"))  # 5위 결정전
    assert SRC.is_target(ref("44441002KTOB02024", "2024-10-02"))  # 와일드카드
    assert SRC.is_target(ref("33331005KTLG02024", "2024-10-05"))  # 준PO
    assert SRC.is_target(ref("55551013LGSS02024", "2024-10-13"))  # PO
    assert SRC.is_target(ref("77771022SSHT02024", "2024-10-22"))  # KS


def test_unknown_prefix_excluded():
    # 새 코드가 나타나면 조용히 수집되지 않고 제외 + run.py 경고로 드러나야 한다
    assert not SRC.is_target(ref("88881022HTSS02024", "2024-10-22"))


def test_regular_game_must_match_its_date():
    assert not SRC.is_target(ref("20240723WOOB02024", "2024-07-24"))


def test_cancelled_game_excluded():
    assert not SRC.is_target(ref("20240629OBLT02024", "2024-06-29", status="CANCEL"))


def test_non_kbo_game_excluded():
    assert not SRC.is_target(ref("20240724XXYY02024", "2024-07-24", category="mlb"))
