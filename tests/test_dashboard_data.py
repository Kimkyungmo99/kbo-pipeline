from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("build_dashboard", Path(__file__).parents[1] / "analysis/build_dashboard.py")
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)


def valid_rows():
    return [{
        "season": 2025, "team_code": str(i), "game_count": 2,
        "batting_game_count": 2, "pitching_game_count": 2,
        "win_count": 1, "loss_count": 1, "draw_count": 0,
        "runs_scored": 5, "runs_allowed": 5,
    } for i in range(10)]


def test_dashboard_rejects_misaligned_result_and_pitch_coverage():
    rows = valid_rows()
    dashboard.validate_rows(rows, [{"season": 2025, "games": 10}])
    rows[0]["pitching_game_count"] = 1
    with pytest.raises(ValueError, match="different games"):
        dashboard.validate_rows(rows, [{"season": 2025, "games": 10}])


def test_dashboard_rejects_missing_join_and_unbalanced_runs():
    rows = valid_rows()
    incomplete = deepcopy(rows)
    incomplete[0]["batting_game_count"] = None
    with pytest.raises(ValueError, match="Missing"):
        dashboard.validate_rows(incomplete, [{"season": 2025, "games": 10}])
    rows[0]["runs_scored"] += 1
    with pytest.raises(ValueError, match="Runs scored"):
        dashboard.validate_rows(rows, [{"season": 2025, "games": 10}])
