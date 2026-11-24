"""Physical-invariance checks and full training/test player-bootstrap uncertainty."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from extract_mirror_features import measure
from analyze_mirror_protection import load_data, preprocessing, player_model, CLASSIC, MIRROR

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/trenches"


def invariant_checks():
    # Known lateral oscillation followed by a separate forward sprint.
    time = np.arange(0, 10.1, .1)
    phase = time <= 8
    x = np.where(phase, 45, 45 + (time - 8) * 4)
    y = np.where(phase, 27 + 2 * np.sin(2 * np.pi * time / 2), 27)
    speed = np.sqrt(np.gradient(x, time) ** 2 + np.gradient(y, time) ** 2)
    frame = pd.DataFrame({"time": pd.Timestamp("2025-01-01") + pd.to_timedelta(time, unit="s"),
                          "x": x, "y": y, "s": speed})
    original, reason, _ = measure(frame)
    assert reason is None and original["reversals"] >= 6
    translated = frame.copy()
    translated["x"] += 100
    translated["y"] -= 80
    reflected = frame.copy()
    reflected["y"] *= -1
    shifted_time = frame.copy()
    shifted_time["time"] += pd.Timedelta(days=10)
    for label, changed in [("coordinate_translation", translated), ("lateral_reflection", reflected),
                           ("timestamp_shift", shifted_time), ("input_row_order", frame.sample(frac=1, random_state=7))]:
        actual, reason, _ = measure(changed)
        assert reason is None, label
        for column in ["lateral_speed_p75", "reversal_recovery", "mirror_duration", "reversals"]:
            assert np.isclose(actual[column], original[column], atol=1e-9), (label, column)
    duplicate = pd.concat([frame, frame.iloc[[10]]])
    assert measure(duplicate)[1] == "invalid_time_or_short"
    gap = frame.drop(index=[20, 21, 22])
    assert measure(gap)[1] == "invalid_time_or_short"
    return ["translation_invariance", "reflection_invariance", "time_origin_invariance", "row_order_invariance",
            "duplicate_timestamp_rejected", "missing_frame_gap_rejected", "synthetic_reversals_detected"]


def main():
    checks = invariant_checks()
    table, plays = load_data()
    train = table.loc[table.draft_year.lt(2025)].reset_index(drop=True)
    test = table.loc[table.draft_year.eq(2025)].reset_index(drop=True)
    train_p = plays.loc[plays.draft_year.lt(2025)].copy()
    test_p = plays.loc[plays.draft_year.eq(2025)].copy()
    num = ["down", "yards_to_go", "dropback_duration", "duration_sq"]
    cat = ["lined_up_position", "offense_formation"]
    grouped = {pid: frame for pid, frame in train_p.groupby("nfl_id")}
    rng = np.random.default_rng(2027)
    samples = []
    for replicate in range(400):
        # Preserve class counts while resampling whole players, never individual plays.
        train_sample = pd.concat([g.iloc[rng.integers(0, len(g), len(g))] for _, g in train.groupby("draft_year")])
        test_sample = test.iloc[rng.integers(0, len(test), len(test))].copy()
        sampled_plays = pd.concat([grouped[pid] for pid in train_sample.nfl_id], ignore_index=True)
        context = make_pipeline(preprocessing(num, cat), LogisticRegression(C=1, max_iter=2000))
        context.fit(sampled_plays[num + cat], sampled_plays.pressure)
        train_residual = pd.Series(100 * (train_p.pressure.to_numpy() - context.predict_proba(train_p[num + cat])[:, 1]),
                                   index=train_p.nfl_id).groupby(level=0).mean()
        test_residual = pd.Series(100 * (test_p.pressure.to_numpy() - context.predict_proba(test_p[num + cat])[:, 1]),
                                  index=test_p.nfl_id).groupby(level=0).mean()
        train_y = train_sample.nfl_id.map(train_residual)
        test_y = test_sample.nfl_id.map(test_residual)
        record = {"replicate": replicate}
        for label, columns in [("classic", CLASSIC), ("mirror", CLASSIC + MIRROR),
                               ("whole_drill", CLASSIC + ["whole_drill_speed"])]:
            model = player_model(columns).fit(train_sample[columns + ["nfl_position"]], train_y)
            prediction = model.predict(test_sample[columns + ["nfl_position"]])
            record[label + "_mae"] = float(np.mean(np.abs(test_y - prediction)))
        record["mirror_improvement"] = record["classic_mae"] - record["mirror_mae"]
        record["whole_drill_improvement"] = record["classic_mae"] - record["whole_drill_mae"]
        samples.append(record)
    results = pd.DataFrame(samples)
    results.to_csv(OUT / "mirror_full_refit_bootstrap.csv", index=False)
    summary = {"status": "passed", "invariant_checks": checks, "bootstrap_replicates": len(results),
               "test_year": 2025,
               "method": "Stratified training-player and test-player resampling, refitting context and player models each replicate.",
               "intervals_pp": {column: results[column].quantile([.025, .975]).tolist()
                                for column in ["mirror_improvement", "whole_drill_improvement"]},
               "limitations": "Exploratory percentile intervals with 400 replicates; conditional on observed games per resampled player; not adjusted for research multiplicity."}
    (OUT / "mirror_validation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
