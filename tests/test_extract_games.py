from ingestion.base import GameRef
from scripts_extract_games import rows_from_refs


def test_result_row_uses_official_schedule_score():
    ref = GameRef(
        game_id="20240702HTSS02024", date="2024-07-02", category="kbo", status="RESULT",
        away_team_code="HT", home_team_code="SS", away_score=9, home_score=5, winner="AWAY",
    )
    row = rows_from_refs([ref])[0]
    assert row["away_score"] == 9
    assert row["home_score"] == 5
    assert row["winner"] == "AWAY"
    assert row["game_type"] == "regular"


def test_result_row_rejects_winner_score_mismatch():
    ref = GameRef(
        game_id="20240702HTSS02024", date="2024-07-02", category="kbo", status="RESULT",
        away_team_code="HT", home_team_code="SS", away_score=9, home_score=5, winner="HOME",
    )
    try:
        rows_from_refs([ref])
    except ValueError as error:
        assert "승자" in str(error)
    else:
        raise AssertionError("winner와 score가 불일치하면 실패해야 합니다")
