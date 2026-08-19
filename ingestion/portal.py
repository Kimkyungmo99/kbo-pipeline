"""네이버 스포츠 비공식 게이트웨이 구현체 (GameSource).

Dagster 비의존 — 순수 Python + httpx 만 사용한다.
"""
from __future__ import annotations

import time

import httpx

from ingestion.base import GameRef, GameSource
from ingestion.parsers import portal as portal_parser


class PortalSource(GameSource):
    def __init__(self, cfg: dict):
        self.cfg = cfg

    @property
    def source_name(self) -> str:
        return "portal"

    # --- HTTP ---

    def _get_json(self, url: str) -> dict:
        r = httpx.get(url, headers=self.cfg["headers"], timeout=10, follow_redirects=True)
        r.raise_for_status()
        time.sleep(self.cfg["delay_seconds"])  # 수집 예의: 요청 간 최소 1초
        return r.json()

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
        """실측 확정 규칙: KBO 리그 + 종료 경기만.
        (취소 경기는 relay null / 비KBO는 RESULT여도 투구 relay 없음)"""
        return ref.category == "kbo" and ref.status == "RESULT"
