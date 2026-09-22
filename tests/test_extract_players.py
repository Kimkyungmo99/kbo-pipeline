import json

from scripts_extract_players import extract_game


def test_extract_game_uses_real_pitches_and_infers_unstructured_pitcher_change(tmp_path):
    path = tmp_path / "game_20250504SKLG02025.json"
    raw = {
        "result": {
            "textRelayData": [{
                "textRelays": [{
                    "homeOrAway": "0",
                    "textOptions": [
                        {
                            "seqno": 1,
                            "pitchNum": 1,
                            "pitchResult": "B",
                            "currentGameState": {"pitcher": "55138", "batter": "10001"},
                            "batterRecord": {"pcode": "10001", "name": "타자A"},
                        },
                        {
                            "seqno": 2,
                            "text": "투수 코엔 윈 : 투수 배재준 (으)로 교체",
                            "currentGameState": {"pitcher": "63145", "batter": "99999"},
                            "playerChange": {"type": "text"},
                        },
                        {
                            "seqno": 3,
                            "pitchNum": 1,
                            "pitchResult": "T",
                            "currentGameState": {"pitcher": "63145", "batter": "10002"},
                            "batterRecord": {"pcode": "10002", "name": "타자B"},
                        },
                    ],
                }],
            }],
        },
    }
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    names, observations = extract_game(path)

    assert names["55138"] == "코엔 윈"
    assert names["63145"] == "배재준"
    assert ("55138", "LG", "pitcher") in observations
    assert ("63145", "LG", "pitcher") in observations
    assert all(player_id != "99999" for player_id, _, _ in observations)
