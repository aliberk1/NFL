import csv
import json

import duckdb
import pytest

from app import analytics
from pipelines import ingest


@pytest.fixture
def csv_data(tmp_path, monkeypatch):
    source = tmp_path / "raw"
    source.mkdir()
    monkeypatch.setattr(ingest, "DATA", source)
    monkeypatch.setattr(ingest, "DB", tmp_path / "curated" / "nfl.duckdb")
    rows = {
        "players": [
            {"nfl_id": 1, "display_name": "A Player", "nfl_position": "QB", "draft_year": 2023},
        ],
        "games": [
            {"game_id": 10, "season": 2023, "season_type": "REG"},
            {"game_id": 20, "season": 2023, "season_type": "REG"},
        ],
        "combine_results": [{"nfl_id": 1, "draft_year": 2023}],
        "player_career_successes": [{"nfl_id": 1}],
        "player_play": [
            {"game_id": 10, "play_id": 1, "nfl_id": 1, "team_abbr": "AAA",
             "pressure_allowed": "true", "rec_yards": 0, "rush_yards": 0, "sack": 0.5},
            {"game_id": 20, "play_id": 1, "nfl_id": 1, "team_abbr": "BBB",
             "pressure_allowed": "false", "rec_yards": 0, "rush_yards": 0, "sack": 0.0},
        ],
    }

    def write():
        for table, records in rows.items():
            with (source / f"{table}.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)

    write()
    return rows, write


def test_report_version_and_historical_teams(csv_data, monkeypatch):
    ingest.build()
    report = json.loads((ingest.DB.parent / "quality_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["seasons"] == [2023]
    assert len(report["data_version"]) == 64
    assert report["loaded_at_utc"].endswith("+00:00")
    assert report["foreign_keys"]["player_play.nfl_id -> players.nfl_id"] == 0
    assert report["tables"]["player_play"]["missing_values"]["sack"] == 0
    with duckdb.connect(str(ingest.DB), read_only=True) as con:
        assert con.execute(
            "SELECT team_abbr, represented_games FROM team_season_coverage ORDER BY team_abbr"
        ).fetchall() == [("AAA", 1), ("BBB", 1)]
    monkeypatch.setattr(analytics, "DB", ingest.DB)
    assert analytics.dataset_summary()["provenance"]["data_version"] == report["data_version"]


@pytest.mark.parametrize("change,expected", [
    (lambda rows: rows["players"][0].pop("display_name"), "eksik kolonlar"),
    (lambda rows: rows["games"][0].update(season="wrong"), "yanlış veri tipleri"),
    (lambda rows: rows["players"][0].update(display_name=""), "boş değer"),
    (lambda rows: rows["player_play"].append(dict(rows["player_play"][0])), "tekrar anahtar"),
    (lambda rows: rows["player_play"][0].update(nfl_id=99), "eşleşmeyen nfl_id"),
])
def test_invalid_data_rejected_with_report(csv_data, change, expected):
    rows, write = csv_data
    change(rows)
    write()
    with pytest.raises(ValueError, match=expected):
        ingest.build()
    report = json.loads((ingest.DB.parent / "quality_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert not ingest.DB.exists()


def test_failed_refresh_keeps_last_valid_database(csv_data):
    rows, write = csv_data
    ingest.build()
    original = ingest.DB.read_bytes()
    rows["players"][0]["display_name"] = ""
    write()
    with pytest.raises(ValueError, match="boş değer"):
        ingest.build()
    assert ingest.DB.read_bytes() == original
