import copy
import json

import duckdb
import numpy as np
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from app import analytics, api, config, similarity
from app.player_view import COMBINE_FIELDS
from pipelines import demo_data, ingest
from scripts import evaluate_similarity as study

FEATURES = similarity.GROUPS["WR"]["features"]


def player(number, position="WR", **changes):
    row = {"nfl_id": number, "display_name": f"P{number}", "nfl_position": position, "draft_year": 2023}
    row.update({name: float(number + index) for index, name in enumerate(FEATURES)})
    return {**row, **changes}


def test_groups_do_not_overlap_and_exclude_outcomes():
    positions = [p for rule in similarity.GROUPS.values() for p in rule["positions"]]
    assert len(positions) == len(set(positions))
    labels = {key for key, _, _ in COMBINE_FIELDS}
    for rule in similarity.GROUPS.values():
        assert set(rule["features"]) <= labels
        assert not any(word in name for name in rule["features"] for word in ("ngs", "draft", "career", "game"))


def test_neighbours_are_same_group_sorted_and_exclude_self():
    pool = [player(n) for n in range(1, 21)] + [player(100, "T")]
    data = similarity.similar(pool[9], pool)
    assert data["status"] == "ok" and data["pool_size"] == 19
    ids = [row["nfl_id"] for row in data["neighbors"]]
    assert ids[:4] == [9, 11, 8, 12] and 10 not in ids and 100 not in ids
    for row in data["neighbors"]:
        assert row["distance_low"] <= row["distance"] <= row["distance_high"]
        assert 0 <= row["stability"] <= 1


@pytest.mark.parametrize("scale", [0.01, 1000])
def test_units_do_not_change_neighbours(scale):
    pool = [player(n, forty=float(n * 7 % 11)) for n in range(1, 21)]
    changed = [{**row, "combine_weight": row["combine_weight"] * scale} for row in pool]
    first, second = (similarity.similar(rows[4], rows)["neighbors"] for rows in (pool, changed))
    assert [r["nfl_id"] for r in first] == [r["nfl_id"] for r in second]
    assert first[0]["distance"] == pytest.approx(second[0]["distance"])


@pytest.mark.parametrize("value", [None, "", float("nan"), "unknown", True])
def test_missing_values_are_not_zero(value):
    assert similarity.number(value) is None


def test_insufficient_measurements_small_pool_and_unsupported_position():
    pool = [player(n) for n in range(1, 21)]
    sparse = player(50, **{name: None for name in FEATURES[4:]})
    assert similarity.similar(sparse, pool)["status"] == "insufficient_measurements"
    assert similarity.similar(pool[0], pool[:10])["status"] == "small_pool"
    assert similarity.similar(player(60, "QB"), pool)["status"] == "unsupported_position"


def test_scaler_uses_reference_pool_only():
    pool = [player(n) for n in range(1, 12)]
    outlier = player(99, combine_weight=1e9)
    data = similarity.similar(outlier, pool)
    assert similarity.fit_scaler(pool, FEATURES)["combine_weight"][1] < 10
    assert data["neighbors"][0]["distance"] > 1e6


@pytest.fixture
def demo(tmp_path, monkeypatch):
    path = tmp_path / "curated" / "nfl.duckdb"
    for module in (analytics, api, config, ingest):
        monkeypatch.setattr(module, "DB", path)
    # A larger fictional roster is needed for a usable pool.
    demo_data.ensure()
    with duckdb.connect(str(path)) as con:
        con.execute("UPDATE players SET nfl_position = 'WR' WHERE nfl_position IN ('TE', 'CB')")
    return path


def test_api_and_ui_show_pool_range_and_caveat(demo):
    with duckdb.connect(str(demo)) as con:
        target = con.execute("SELECT nfl_id FROM players JOIN combine_results USING (nfl_id) "
                             "WHERE nfl_position = 'WR' AND forty IS NOT NULL ORDER BY nfl_id LIMIT 1").fetchone()[0]
    payload = TestClient(api.app).get(f"/players/{target}/similar").json()
    assert payload["kind"] == "synthetic_demo" and payload["data"]["status"] == "ok"
    assert payload["data"]["pool_size"] >= similarity.MIN_POOL and len(payload["data"]["neighbors"]) == 5
    assert TestClient(api.app).get("/players/1/similar").json()["data"]["status"] == "player_not_found"
    app = AppTest.from_file(str(config.ROOT / "app" / "ui.py"), default_timeout=30).run()
    option = next(o for o in app.multiselect[0].options if o.endswith(f"#{target}"))
    app.multiselect[0].select(option).run()
    assert not app.exception
    captions = [item.value for item in app.caption]
    assert any("Karşılaştırma havuzu" in text for text in captions)
    assert analytics.SIMILARITY_NOTES[0] in captions


@pytest.mark.parametrize("name", list(study.STUDIES))
def test_no_leakage_from_test_class_into_training(name):
    rows, features = study.load(name), similarity.GROUPS[name]["features"]
    train = [row for row in rows if row["draft_year"] == 2023]
    test = [row for row in rows if row["draft_year"] == 2024]
    base, _ = study.predict(train, test, features)
    changed = copy.deepcopy(test)
    for row in changed:
        row["target"] = 1e6
    changed[-1].update({f: 1e6 for f in features})
    after, _ = study.predict(train, changed, features)
    for model in base:
        # Test outcomes and another test player's measurements cannot affect a prediction.
        np.testing.assert_allclose(base[model][:-1], after[model][:-1])


def test_training_years_must_precede_test_year():
    with pytest.raises(ValueError, match="precede"):
        study.evaluate([], FEATURES, [2024], 2024)


def test_recorded_result_matches_inputs_code_and_point_estimates(monkeypatch):
    recorded = analytics.similarity_study()["summary"]
    for group in ("inputs_sha256", "code_sha256"):
        for path, digest in recorded[group].items():
            assert study.text_hash(study.ROOT / path) == digest, f"{path}: run python -m scripts.evaluate_similarity"
    assert recorded["settings"] == study.SETTINGS
    monkeypatch.setitem(study.SETTINGS, "bootstrap_resamples", 5)
    fresh = study.run()
    for name, item in recorded["studies"].items():
        for old, new in zip(item["folds"], fresh["studies"][name]["folds"], strict=True):
            assert old["test_players"] == new["test_players"]
            for a, b in zip(old["scores"], new["scores"], strict=True):
                assert a["model"] == b["model"] and a["mae"] == pytest.approx(b["mae"], abs=2e-6)


def test_report_claim_follows_intervals_and_contains_no_player_rows():
    summary = analytics.similarity_study()["summary"]
    lows = [score["ci_low"] for item in summary["studies"].values() for fold in item["folds"]
            for score in fold["scores"] if score["model"] == "similar_k5"]
    assert summary["consistent_benefit_shown"] is all(low > 0 for low in lows)
    assert summary["independent_validation"] == "not_performed"
    assert "nfl_id" not in json.dumps(summary) and "display_name" not in json.dumps(summary)
