"""Explicitly post-hoc diagnostics; they do not replace the primary design."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_speed_transfer import context_model, player_model, CAT, NUM, BASE

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/nfl-big-data-bowl-2027"
PROCESSED = ROOT / "data/processed"
OUT = ROOT / "reports/speed_study"


def correlation_interval(x, y, seed=2027):
    values = np.column_stack([x, y])
    values = values[np.isfinite(values).all(axis=1)]
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(3000):
        sample = values[rng.integers(0, len(values), len(values))]
        if sample[:, 0].std() > 0 and sample[:, 1].std() > 0:
            stats.append(np.corrcoef(sample.T)[0, 1])
    return {"n": len(values), "r": float(np.corrcoef(values.T)[0, 1]),
            "ci_low": float(np.quantile(stats, .025)), "ci_high": float(np.quantile(stats, .975))}


def main():
    raw = pd.read_csv(OUT / "descriptive_player_means.csv")
    correlations = []
    for year, g in [("pooled", raw)] + list(raw.groupby("draft_year")):
        correlations.append({"comparison": "combine_peak_vs_game_speed", "year": str(year),
                             **correlation_interval(g.combine_peak_speed, g.game_peak_speed)})
    demeaned = raw[["combine_peak_speed", "game_peak_speed"]] - raw.groupby("draft_year")[[
        "combine_peak_speed", "game_peak_speed"]].transform("mean")
    correlations.append({"comparison": "combine_peak_vs_game_speed", "year": "within_year_demeaned",
                         **correlation_interval(demeaned.combine_peak_speed, demeaned.game_peak_speed)})
    correlations.append({"comparison": "combine_peak_vs_official_forty", "year": "pooled",
                         **correlation_interval(raw.combine_peak_speed, raw.forty)})

    players = pd.read_csv(DATA / "players.csv")
    attempts = pd.read_csv(PROCESSED / "combine_speed_attempts.csv").merge(
        players[["nfl_id", "draft_year"]], on="nfl_id", validate="many_to_one")
    attempts = attempts.sort_values(["nfl_id", "attempt", "event_id"])
    attempts["repeat_index"] = attempts.groupby("nfl_id").cumcount()
    pairs = attempts.loc[attempts.repeat_index.lt(2)].pivot(
        index=["nfl_id", "draft_year"], columns="repeat_index",
        values=["combine_peak_speed", "combine_early_speed"])
    repeat_records = []
    for feature in ["combine_peak_speed", "combine_early_speed"]:
        values = pairs[feature].dropna()
        for year, g in [("pooled", values)] + list(values.groupby(level="draft_year")):
            repeat_records.append({"feature": feature, "year": str(year), **correlation_interval(g[0], g[1])})
    attempts.groupby("draft_year")[["combine_peak_speed", "combine_early_speed"]].agg(
        ["count", "median", "std", "min", "max"]).to_csv(OUT / "speed_feature_year_distributions.csv")

    # A single diagnostic ablation, motivated by low observed early-speed repeatability.
    table = pd.read_csv(OUT / "player_features.csv")
    plays = pd.read_csv(PROCESSED / "rookie_wr_route_speed.csv")
    plays = plays.loc[plays.nfl_id.isin(table.nfl_id)].copy()
    ablation = []
    for year in (2024, 2025):
        train_p, test_p = plays.loc[plays.draft_year.lt(year)].copy(), plays.loc[plays.draft_year.eq(year)].copy()
        context = context_model().fit(train_p[CAT + NUM], train_p.game_peak_speed)
        for frame in (train_p, test_p):
            frame["target"] = frame.game_peak_speed - context.predict(frame[CAT + NUM])
        train = table.merge(train_p.groupby("nfl_id").target.mean(), on="nfl_id")
        test = table.merge(test_p.groupby("nfl_id").target.mean(), on="nfl_id")
        for label, columns in [("traditional", BASE), ("classic_plus_peak_only_POST_HOC", BASE + ["combine_peak_speed"])]:
            model = player_model().fit(train[columns], train.target)
            prediction = model.predict(test[columns])
            ablation.append({"test_year": year, "model": label, "test_players": len(test),
                             "mae": float(np.mean(np.abs(test.target - prediction))),
                             "rmse": float(np.sqrt(np.mean((test.target - prediction) ** 2)))})
    pd.DataFrame(ablation).to_csv(OUT / "post_hoc_peak_only_ablation.csv", index=False)
    pd.DataFrame(correlations).to_csv(OUT / "correlation_diagnostics.csv", index=False)
    pd.DataFrame(repeat_records).to_csv(OUT / "combine_repeatability_intervals.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for ax, feature, title in zip(axes, ["combine_peak_speed", "combine_early_speed"],
                                  ["40-yard peak speed", "Early-speed proxy"]):
        values = pairs[feature].dropna()
        for year, group in values.groupby(level="draft_year"):
            ax.scatter(group[0], group[1], label=str(year), alpha=.75)
        lo, hi = values.min().min(), values.max().max()
        ax.plot([lo, hi], [lo, hi], "--", color="gray", linewidth=1)
        record = next(r for r in repeat_records if r["feature"] == feature and r["year"] == "pooled")
        ax.set(xlabel="First tracked attempt", ylabel="Second tracked attempt",
               title=f"{title}: r={record['r']:.2f}, n={record['n']}")
        ax.legend(title="Draft year", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "combine_repeatability.png", dpi=160)
    plt.close(fig)
    result = {"status": "post-hoc diagnostics, not a replacement primary analysis",
              "correlations": correlations, "repeatability": repeat_records, "ablation": ablation,
              "interval_note": "Player bootstrap; within-year demeaning fixed before resampling. Exploratory, no multiplicity adjustment."}
    (OUT / "robustness.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
