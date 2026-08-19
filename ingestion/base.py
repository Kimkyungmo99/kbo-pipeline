"""소스 어댑터 인터페이스 (계획서 4장).

원칙: 구현체는 Dagster를 임포트하지 않는다 (오케스트레이터 비의존).
계획서 인터페이스에 fetch_raw/parse 분리를 추가했다 — 이유:
(1) raw JSON 원본 보존(감사 추적·재파싱)이 수집 계층의 책임이고,
(2) 파서를 네트워크 없이 테스트할 수 있어야 하기 때문 (D3 원칙).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GameRef:
    """경기 참조 — 목록 API가 주는 것만 담는다. ID는 역산하지 않는다."""
    game_id: str
    date: str  # YYYY-MM-DD
    category: str | None = None  # 예: "kbo" (비KBO 경기는 투구 relay 없음)
    status: str | None = None    # 예: "RESULT" (취소 경기는 relay null)
    home: str | None = None
    away: str | None = None


class GameSource(ABC):
    """데이터 소스 1개 = 구현체 1개. 새 소스(공식 기록실 등)는 이 클래스만 구현하면 된다."""

    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @abstractmethod
    def list_games(self, target: str) -> list[GameRef]:
        """해당 날짜(YYYY-MM-DD)의 전체 경기 목록 (필터 전)."""

    @abstractmethod
    def fetch_raw(self, ref: GameRef) -> dict:
        """경기 1개의 원본 응답. 호출자가 data/raw/ 에 그대로 보존한다."""

    @abstractmethod
    def parse_pitches(self, raw: dict, game_id: str) -> list[dict]:
        """원본 → 투구 단위 행. 순수 함수여야 한다 (네트워크·IO 금지)."""

    def fetch_pitches(self, ref: GameRef) -> list[dict]:
        """계획서 4장의 원 인터페이스 — fetch_raw + parse의 조합."""
        return self.parse_pitches(self.fetch_raw(ref), ref.game_id)

    def is_target(self, ref: GameRef) -> bool:
        """수집 대상 판별. 기본: 전부 대상. 구현체가 오버라이드."""
        return True
