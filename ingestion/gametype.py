"""gameId → 경기 종류 분류 (순수 함수).

실측 (2026-09-10~11, probe_list.py): gameId 앞 4자리는 연도가 아니라 **경기 종류 코드**다.
MMDD·팀코드·경기번호·시즌은 그대로이고 앞 4자리만 바뀐다.

    20240928HTLT02024   정규 (앞 8자리 = 경기 날짜)
    66661001SKKT02024   순위 결정전 (2024-10-01 5위 타이브레이크 SSG-KT)
    44441002KTOB02024   와일드카드 (2024-10-02)
    33331005KTLG02024   준플레이오프 (2024-10-05)
    55551013LGSS02024   플레이오프 (2024-10-13)
    77771022SSHT02024   한국시리즈 (2024-10-22)
    99990706WEEA02024   올스타전 (2024-07-06)

    20250308HTLT02025   시범경기 (정규와 형식 동일 — 시즌 개막일 이전이면 exhibition)

접두·개막일은 실측된 것만 등록한다 — 추측으로 넣지 않는다. 미등록 접두·미등록 시즌은 "unknown"으로
분류되고 수집에서 제외되며 run.py가 경고를 찍는다 (조용히 빠지는 일이 없게).
분류가 gameId만으로 결정되므로 bronze의 game_type 컬럼은 raw 재파싱만으로 재생산된다.
"""
from __future__ import annotations

from datetime import datetime

GAME_TYPE_BY_PREFIX: dict[str, str] = {
    "3333": "semi_po",     # 준플레이오프
    "4444": "wildcard",    # 와일드카드 결정전
    "5555": "po",          # 플레이오프
    "6666": "tiebreaker",  # 순위 결정전 (정규시즌 기록 포함 여부는 dbt에서 결정)
    "7777": "ks",          # 한국시리즈 (77771022SSHT02024 — 2024-10-22, 우천 취소 상태로 실측)
    "9999": "allstar",     # 올스타전 (이벤트전 — 수집 제외)
}

# 시즌별 정규시즌 개막일 (YYYYMMDD) — 시범경기는 gameId 형식이 정규와 완전히 같아서
# (2025-03-08 vs 03-22 목록 객체 전 필드 동일 실측) 개막일 이전 여부로만 구분할 수 있다.
# 접두 사전과 같은 원칙: 확인된 시즌만 등록, 미등록 시즌은 unknown으로 드러낸다 (조용히 regular로 두지 않음).
# 출처: KBO 공지 — 2024 3/23, 2025 3/22, 2026 3/28(시범 3/12~24, WBC로 늦은 개막)
SEASON_OPENING: dict[str, str] = {
    "2024": "20240323",
    "2025": "20250322",
    "2026": "20260328",
}

# 수집 대상 종류 — 올스타·unknown 제외. 시범경기는 수집하되 라벨로 구분 (2026-09-13 결정)
TARGET_GAME_TYPES = frozenset({"regular", "exhibition", "tiebreaker", "wildcard", "semi_po", "po", "ks"})
POSTSEASON_GAME_TYPES = frozenset({"wildcard", "semi_po", "po", "ks"})


def _is_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y%m%d")
        return True
    except ValueError:
        return False


def classify_game_type(game_id: str) -> str:
    """'regular' | 'exhibition' | 'tiebreaker' | 'wildcard' | 'semi_po' | 'po' | 'ks' | 'allstar' | 'unknown'"""
    if game_id[:4] in GAME_TYPE_BY_PREFIX:
        return GAME_TYPE_BY_PREFIX[game_id[:4]]
    # 정규 형식: 앞 8자리가 날짜이고, 앞 4자리(연도)가 끝 4자리(시즌)와 같다.
    # 연도 일치 조건이 없으면 "7777..."처럼 미등록 코드도 날짜로 파싱돼 정규로 오분류된다.
    if not (_is_date(game_id[:8]) and game_id[:4] == game_id[-4:]):
        return "unknown"
    season = game_id[-4:]
    opening = SEASON_OPENING.get(season)
    if opening is None:
        return "unknown"  # 개막일 미등록 시즌 → run.py 경고로 드러남. SEASON_OPENING에 등록하면 해결
    return "exhibition" if game_id[:8] < opening else "regular"
