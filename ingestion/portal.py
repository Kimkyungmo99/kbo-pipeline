"""네이버 스포츠 비공식 게이트웨이 구현체 (GameSource).

Dagster 비의존 — 순수 Python + httpx 만 사용한다.
"""
from __future__ import annotations

import time

import httpx

from ingestion.base import GameRef, GameSource
from ingestion.gametype import TARGET_GAME_TYPES, classify_game_type
from ingestion.parsers import portal as portal_parser


class PortalSource(GameSource):
    def __init__(self, cfg: dict):
        self.cfg = cfg

    @property
    def source_name(self) -> str:
        return "portal"

    # --- HTTP ---

    def _get_json(self, url: str) -> dict:
        """수집 예의 (계획서 4장): 요청 간 1초 딜레이, 실패 시 지수 백오프 최대 3회.

        4xx는 재시도해도 소용없으므로 즉시 올린다 (이닝 루프 종료 판단에도 쓰임).
        5xx·네트워크 오류만 1s → 2s → 4s 백오프 후 재시도.
        """
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                r = httpx.get(url, headers=self.cfg["headers"], timeout=10,
                              follow_redirects=True)
                r.raise_for_status()
                time.sleep(self.cfg["delay_seconds"])
                return r.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500:
                    raise
                last_err = e
            except httpx.TransportError as e:
                last_err = e
            time.sleep(2 ** attempt)
        raise last_err

    # --- GameSource 구현 ---

    def list_games(self, target: str) -> list[GameRef]:
        raw = self._get_json(self.cfg["game_list_url"].format(date=target))
        return [
            GameRef(
                game_id=g["gameId"],
                date=target,
                category=g.get("categoryId"),
                status=g.get("statusCode"),
                home=g.get("homeTeamName"),
                away=g.get("awayTeamName"),
            )
            for g in raw.get("result", {}).get("games", [])
        ]

    def fetch_raw(self, ref: GameRef) -> dict:
        """relay 전체. 이닝별 분할 응답이면 1~12회 루프로 병합."""
        base = self.cfg["pitch_url"].format(game_id=ref.game_id)
        raw = self._get_json(base)

        merged = dict(raw)
        relays = portal_parser.extract_text_relays(raw)
        seen_innings = {r.get("inn") or r.get("inning") for r in relays}
        if len(seen_innings - {None}) <= 1:
            chunks = []
            for inning in range(1, 13):
                try:
                    part = self._get_json(f"{base}?inning={inning}")
                except httpx.HTTPStatusError:
                    break
                part_relays = portal_parser.extract_text_relays(part)
                if not part_relays:
                    break
                chunks.append({"textRelays": part_relays})
            if chunks:
                merged = {"result": {"textRelayData": chunks}}
        return merged

    def parse_pitches(self, raw: dict, game_id: str) -> list[dict]:
        return portal_parser.parse_pitches(raw, game_id)

    def is_target(self, ref: GameRef) -> bool:
        """실측 확정 규칙: KBO 리그 + 종료 경기 + 알려진 공식 경기 종류(올스타 제외).

        - 취소 경기는 relay null / 비KBO는 RESULT여도 투구 relay 없음
        - 경기 종류는 gameId 접두로 판별 (gametype.py): 정규·순위결정전·포스트시즌은 수집,
          올스타전(9999)은 이벤트전이라 제외, 미확인 접두는 제외 + run.py가 경고
        - 정규 경기는 gameId 앞 8자리 = 경기 날짜여야 한다 (한 번 더 잠금)
        이력: 처음엔 "앞 8자리 = 날짜"만 썼는데 그 규칙은 포스트시즌·타이브레이크까지
        걸러낸다는 걸 2026-09-10 probe로 확인 → 종류 기반으로 교체.
        """
        if ref.category != "kbo" or ref.status != "RESULT":
            return False
        gtype = classify_game_type(ref.game_id)
        if gtype == "regular":
            return ref.game_id.startswith(ref.date.replace("-", ""))
        return gtype in TARGET_GAME_TYPES
