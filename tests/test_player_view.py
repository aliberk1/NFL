import duckdb
from pathlib import Path
import streamlit
from streamlit.testing.v1 import AppTest

from app import analytics, config
from app.player_view import (
    COMBINE_FIELDS, comparison_groups, formatted_fields, position_label, role_for_position, team_label,
)


def test_presentation_keeps_missing_distinct_from_zero():
    rows = formatted_fields({"forty": None, "bench_reps": 0}, COMBINE_FIELDS)
    values = {row["Alan"]: row["Değer"] for row in rows}
    assert values["40 yard süresi"] == "Bilgi yok"
    assert values["Bench press"] == "0 tekrar"
    assert team_label("MIN") == "Minnesota Vikings (MIN)"
    assert position_label("WR") == "Pas yakalayıcı (WR)"


def test_comparison_uses_role_metric_and_weighted_rate():
    base = {"season": 2025, "season_type": "REG", "sacks": None,
            "sack_labeled_plays": 0, "tackles": None, "tackle_labeled_plays": 0,
            "receiving_yards": None, "receiving_labeled_plays": 0,
            "rushing_yards": None, "rushing_labeled_plays": 0}
    rows = [
        {**base, "nfl_id": 1, "display_name": "Line Player", "nfl_position": "T",
         "team_abbr": "MIN", "games": 2, "pressure_allowed_rate": 0.1,
         "pressure_labeled_plays": 10},
        {**base, "nfl_id": 1, "display_name": "Line Player", "nfl_position": "T",
         "team_abbr": "NYG", "games": 1, "pressure_allowed_rate": 0.4,
         "pressure_labeled_plays": 5},
        {**base, "nfl_id": 2, "display_name": "Receiver", "nfl_position": "WR",
         "team_abbr": "MIN", "games": 2, "pressure_allowed_rate": None,
         "pressure_labeled_plays": 0, "receiving_yards": 45,
         "receiving_labeled_plays": 2},
    ]
    groups = comparison_groups(rows)
    assert role_for_position("T") == "Hücum hattı"
    assert groups["Hücum hattı"][0]["Değer"] == 20.0
    assert groups["Hücum hattı"][0]["Etiketli kayıt"] == 15
    assert groups["Pas yakalayıcı"][0]["Değer"] == 45
    assert groups["Pas yakalayıcı"][0]["Etiketli kayıt"] == 2
    legacy = dict(rows[-1])
    del legacy["receiving_labeled_plays"]
    assert comparison_groups([legacy])["Pas yakalayıcı"][0]["Etiketli kayıt"] is None


def test_main_flow_preserves_selection_across_search_and_filters(tmp_path, monkeypatch):
    monkeypatch.setattr(streamlit, "image", lambda *args, **kwargs: None)
    monkeypatch.setattr(streamlit, "dataframe", lambda *args, **kwargs: None)
    path = tmp_path / "ui.duckdb"
    with duckdb.connect(str(path)) as con:
        con.execute("CREATE TABLE players (nfl_id BIGINT, display_name VARCHAR, nfl_position VARCHAR, draft_year BIGINT)")
        con.execute("INSERT INTO players VALUES (1, 'Test Receiver', 'WR', 2025), (2, 'Test Lineman', 'T', 2025)")
        con.execute("CREATE TABLE games (game_id BIGINT, season BIGINT, season_type VARCHAR)")
        con.execute("INSERT INTO games VALUES (10, 2025, 'REG'), (20, 2024, 'REG')")
        con.execute("""CREATE TABLE player_play (
            game_id BIGINT, play_id BIGINT, nfl_id BIGINT, team_abbr VARCHAR,
            pressure_allowed BOOLEAN, rec_yards BIGINT, rush_yards BIGINT,
            sack DOUBLE, tackle BIGINT)""")
        con.execute("""INSERT INTO player_play VALUES
            (10, 1, 1, 'MIN', NULL, 40, NULL, NULL, NULL),
            (20, 1, 1, 'NYG', NULL, 10, NULL, NULL, NULL),
            (10, 1, 2, 'MIN', true, NULL, NULL, NULL, NULL)""")
        con.execute("CREATE TABLE combine_results (nfl_id BIGINT, draft_year BIGINT, forty DOUBLE)")
        con.execute("INSERT INTO combine_results VALUES (1, 2025, 4.5)")
        con.execute("CREATE TABLE player_career_successes (nfl_id BIGINT, career_games_active BIGINT)")
        con.execute("INSERT INTO player_career_successes VALUES (1, 1)")
        con.execute("""CREATE VIEW team_season_coverage AS
            SELECT pp.team_abbr, g.season, count(DISTINCT pp.nfl_id) represented_players,
                   count(DISTINCT pp.game_id) represented_games,
                   count(DISTINCT pp.play_id) represented_plays, count(*) player_play_rows
            FROM player_play pp JOIN games g USING(game_id)
            GROUP BY pp.team_abbr, g.season""")
    monkeypatch.setattr(analytics, "DB", path)
    monkeypatch.setattr(config, "DB", path)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app" / "ui.py"),
                            default_timeout=20).run()
    assert not app.exception
    app.text_input[0].set_value("Test Receiver").run()
    app.button[0].click().run()
    assert not app.exception
    assert app.multiselect[0].value == [1]
    app.text_input[0].set_value("not found").run()
    assert not app.exception
    assert app.multiselect[0].value == [1]
    app.text_input[0].set_value("").run()
    next(item for item in app.selectbox if item.label == "Takım").set_value("MIN").run()
    assert not app.exception
    assert app.multiselect[0].value == [1]
    assert any("Minnesota Vikings (MIN)" in item.value for item in app.caption)
    next(item for item in app.selectbox if item.label == "Pozisyon").set_value("T").run()
    assert not app.exception
    assert app.multiselect[0].value == [1]
    assert any("Bu pozisyonda seçili oyuncu yok" in item.value for item in app.info)
    next(item for item in app.selectbox if item.label == "Pozisyon").set_value("Tümü").run()
    next(item for item in app.selectbox if item.label == "Sezon").set_value(2024).run()
    assert any("kayıt bulunamadı" in item.value for item in app.info)
