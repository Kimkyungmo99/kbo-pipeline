"""목록 API의 공식 최종 스코어를 날짜별 경기 Parquet으로 저장한다.

사용:
    py scripts_extract_games.py             # 로컬 raw가 있는 모든 날짜
    py scripts_extract_games.py 2026-09-29  # 한 날짜만 처리
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

from ingestion import storage
from ingestion.gametype import classify_game_type
from ingestion.run import get_s3_or_none, make_source

RAW_ROOT = Path("data/raw/source=portal")
OUT_ROOT = Path("data/bronze_games")


def rows_from_refs(refs) -> list[dict]:
    rows = []
    for ref in refs:
        if ref.home_score is None or ref.away_score is None:
            raise ValueError(f"{ref.game_id}: 완료 경기인데 최종 스코어가 없습니다")
        expected_winner = "HOME" if ref.home_score > ref.away_score else "AWAY" if ref.away_score > ref.home_score else "DRAW"
        if ref.winner != expected_winner:
            raise ValueError(f"{ref.game_id}: winner={ref.winner}, score가 뜻하는 승자={expected_winner}")
        rows.append({
            "game_date": ref.date,
            "game_id": ref.game_id,
            "season": int(ref.game_id[-4:]),
            "game_type": classify_game_type(ref.game_id),
            "away_team_code": ref.away_team_code,
            "home_team_code": ref.home_team_code,
            "away_score": ref.away_score,
            "home_score": ref.home_score,
            "winner": ref.winner,
        })
    return rows


def write_date(refs, dt: str, s3=None) -> Path | None:
    rows = rows_from_refs(refs)
    if not rows:
        print(f"[{dt}] 완료된 경기 결과 없음")
        return None
    out = OUT_ROOT / f"dt={dt}" / "games.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).with_columns(pl.col("game_date").str.to_date()).write_parquet(out, compression="zstd")
    if s3 is not None:
        storage.upload_file(s3, out, f"bronze_games/dt={dt}/games.parquet")
    print(f"[{dt}] 경기 결과 {len(rows)}행")
    return out


def main() -> None:
    requested = sys.argv[1] if len(sys.argv) > 1 else None
    dates = [requested] if requested else [p.name.removeprefix("dt=") for p in sorted(RAW_ROOT.glob("dt=*"))]
    source = make_source()
    s3 = get_s3_or_none()
    game_total = 0
    for dt in dates:
        refs = [ref for ref in source.list_games(dt) if source.is_target(ref)]
        if write_date(refs, dt, s3=s3) is not None:
            game_total += len(refs)
    print(f"완료: {len(dates)}일, 경기 결과 {game_total}행")


if __name__ == "__main__":
    main()
