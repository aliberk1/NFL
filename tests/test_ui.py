from pathlib import Path

import pytest
import streamlit
from streamlit.testing.v1 import AppTest

from app import analytics, assistant, config


@pytest.fixture
def ui(monkeypatch, tmp_path):
    monkeypatch.setattr(streamlit, "image", lambda *args, **kwargs: None)
    monkeypatch.setattr(streamlit, "dataframe", lambda *args, **kwargs: None)
    database = tmp_path / "ui.duckdb"
    database.touch()
    monkeypatch.setattr(config, "DB", database)
    monkeypatch.setattr(analytics, "DB", database)
    players = [
        {"nfl_id": 1, "display_name": "A Player", "nfl_position": "WR", "draft_year": 2023, "teams": "MIN, NYJ"},
        {"nfl_id": 2, "display_name": "B Player", "nfl_position": "WR", "draft_year": 2023, "teams": "MIN"},
        {"nfl_id": 3, "display_name": "C Player", "nfl_position": "QB", "draft_year": 2024, "teams": "BUF"},
    ]
    monkeypatch.setattr(analytics, "player_filter_options", lambda: {"data": {
        "positions": [{"nfl_position": "QB"}, {"nfl_position": "WR"}],
        "draft_years": [{"draft_year": 2024}, {"draft_year": 2023}],
    }})

    def directory(search="", position=None, draft_year=None, limit=100, offset=0, team=None, paginated=False):
        rows = [p for p in players if
                (not search or search.casefold() in (p["display_name"] + p["teams"]).casefold()) and
                (not position or p["nfl_position"] == position) and
                (not team or team in p["teams"].split(", ")) and
                (draft_year is None or p["draft_year"] == draft_year)]
        return {"data": {"rows": rows[offset:offset + limit], "total": len(rows), "limit": limit, "offset": offset}}

    monkeypatch.setattr(analytics, "player_directory", directory)
    monkeypatch.setattr(analytics, "dataset_summary", lambda: {"data": {"seasons": [], "coverage": []}})
    monkeypatch.setattr(analytics, "research_snapshot", lambda: {
        "ol": {
            "summary": {"scores": [
                {"variant": "primary_with_duration", "test_year": 2025, "model": "classic", "mae_pp": 0.1},
                {"variant": "primary_with_duration", "test_year": 2025, "model": "mirror_phase", "mae_pp": 0.09,
                 "improvement_over_classic_pp": 0.01, "ci_low": -0.01, "ci_high": 0.03},
            ], "limitations": []},
            "measurements": {"ol_drill_suite": [{"drill": "Pass-Pro Mirror Drill", "accepted_players": 1,
                "peak_in_exit_fraction": 0.5, "phase_vs_whole_spearman": 0.1}]},
            "cohort": [{"display_name": "Linemen", "nfl_position": "T", "draft_year": 2023,
                "lateral_speed_p75": 1, "whole_drill_speed": 1, "lateral_speed_p75_percentile": 1,
                "whole_drill_speed_percentile": 1, "rank_difference_pp": 0}],
            "explorer_html": "", "model_chart": b"", "digests": {},
        },
        "wr": {
            "summary": {"primary_players": 1, "primary_plays": 1, "raw_peak_game_correlation": 0,
                "scores": [{"test_year": 2025, "train_players": 1, "test_players": 1,
                    "traditional_mae": 1, "with_tracking_mae": 1, "movement_mae_improvement": 0,
                    "ci_low": -1, "ci_high": 1}], "limitations": []},
            "cohort": [{"display_name": "Receiver", "nfl_position": "WR", "draft_year": 2023, "forty": 4.5,
                "combine_peak_speed": 1, "combine_early_speed": 1, "game_peak_speed": 1,
                "valid_game_plays": 1}], "model_chart": b"", "digests": {},
        },
    })
    monkeypatch.setattr(analytics, "player_performance", lambda *args, **kwargs: {"data": []})
    monkeypatch.setattr(analytics, "player_profile", lambda player_id: {"data": {
        "player": [], "combine": [], "career_snapshot": [],
    }})
    monkeypatch.setattr(assistant, "answer", lambda question, history: {
        "answer": "Test yanıtı", "evidence": [],
    })
    return AppTest.from_file(str(Path(__file__).parents[1] / "app" / "ui.py"), default_timeout=20).run()


def test_player_filters_and_empty_results(ui):
    assert not ui.exception
    assert any("3 oyuncu" in item.value for item in ui.caption)
    assert "A Player" in ui.multiselect[0].options[0]
    ui.text_input[0].set_value("not-a-player").run()
    assert any("Oyuncu bulunamadı" in item.value for item in ui.info)


def test_multi_team_search_and_same_context_comparison(ui):
    ui.text_input[0].set_value("NYJ").run()
    assert "A Player" in ui.multiselect[0].options[0]
    ui.text_input[0].set_value("").run()
    labels = ui.multiselect[0].options
    ui.multiselect[0].set_value(labels[:2]).run()
    assert any(item.value == "Sezon performansı" for item in ui.subheader)
    assert any("A Player" in item.value and "B Player" in item.value for item in ui.markdown)


def test_compare_warns_when_position_or_draft_differs(ui):
    labels = ui.multiselect[0].options
    ui.multiselect[0].set_value([labels[0], labels[2]]).run()
    assert any("aynı pozisyon ve draft sınıfında" in item.value for item in ui.warning)


def test_chat_ui_submits_question_and_renders_response(ui):
    assert ui.chat_input
    ui.chat_input[0].set_value("Dataset hakkında soru").run()
    assert any(message.value == "Test yanıtı" for message in ui.markdown)
