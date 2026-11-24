"""Predefined route subsets, forward-year evaluation, and feature quality audit."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from wr_pilot import BASE, EXTRA, DATA, numeric_model

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/wr_route_analysis"
SCENARIOS = [("all_routes", 30), ("hitch", 10), ("hitch_man", 5)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    players = pd.read_csv(DATA / "players.csv")
    wr = players.loc[players.nfl_position.eq("WR")]
    attempts = pd.read_csv(ROOT / "reports/wr_pilot/combine_attempt_features.csv")
    feature = attempts.groupby("nfl_id")[EXTRA].median().reset_index()
    table = wr.merge(pd.read_csv(DATA / "combine_results.csv"), on=["nfl_id", "draft_year"])
    table = table.merge(feature, on="nfl_id", validate="one_to_one")
    cols = ["game_id", "play_id", "nfl_id", "route_ran", "separation_at_pass_forward",
            "team_coverage_man_zone", "cushion", "down", "yards_to_go", "play_nullified_by_penalty"]
    plays = pd.read_csv(DATA / "player_play.csv", usecols=cols)
    duplicate_count = int(plays.duplicated(["game_id", "play_id", "nfl_id"]).sum())
    if duplicate_count:
        raise ValueError(f"Unexpected duplicate player-play keys: {duplicate_count}")
    games = pd.read_csv(DATA / "games.csv")
    plays = plays.merge(games[["game_id", "season", "season_type"]], on="game_id", validate="many_to_one")
    plays = plays.merge(wr[["nfl_id", "draft_year"]], on="nfl_id", validate="many_to_one")
    plays = plays.loc[plays.season_type.eq("REG") & plays.season.eq(plays.draft_year) &
                      plays.play_nullified_by_penalty.eq("N") & plays.route_ran.notna() &
                      plays.separation_at_pass_forward.notna() & plays.nfl_id.isin(table.nfl_id)].copy()
    plays.groupby(["draft_year", "route_ran", "team_coverage_man_zone"]).agg(
        plays=("nfl_id", "size"), players=("nfl_id", "nunique")).to_csv(OUT / "route_coverage_counts.csv")
    quality = attempts.merge(wr[["nfl_id", "draft_year"]], on="nfl_id")
    quality.groupby("draft_year")[EXTRA].agg(["count", "median", "min", "max"]).to_csv(OUT / "feature_quality_by_year.csv")
    rejected = pd.read_csv(ROOT / "reports/wr_pilot/rejected_attempts.csv").merge(
        wr[["nfl_id", "draft_year"]], on="nfl_id")
    rejected.groupby(["draft_year", "reason"]).size().to_csv(OUT / "rejections_by_year.csv")
    results, predictions, reliability = [], [], []
    for scenario, minimum in SCENARIOS:
        subset = plays.copy()
        if scenario != "all_routes":
            subset = subset.loc[subset.route_ran.eq("HITCH")].copy()
        if scenario == "hitch_man":
            subset = subset.loc[subset.team_coverage_man_zone.eq("MAN_COVERAGE")].copy()
        counts = subset.groupby("nfl_id").size()
        eligible = counts[counts >= minimum].index
        subset = subset.loc[subset.nfl_id.isin(eligible)].copy()
        # Descriptive split-half reliability of raw outcomes, not a selection criterion.
        ordered = subset.sort_values(["nfl_id", "game_id", "play_id"]).copy()
        ordered["half"] = ordered.groupby("nfl_id").cumcount() % 2
        halves = ordered.groupby(["nfl_id", "half"]).separation_at_pass_forward.mean().unstack()
        correlation = halves[0].corr(halves[1]) if len(halves) > 2 else np.nan
        reliability.append({"scenario": scenario, "players": len(halves),
                            "odd_even_raw_outcome_correlation": correlation})
        for year in (2024, 2025):
            train_p = subset.loc[subset.draft_year.lt(year)].copy()
            test_p = subset.loc[subset.draft_year.eq(year)].copy()
            record = {"scenario": scenario, "minimum_plays": minimum, "test_year": year,
                      "train_players": train_p.nfl_id.nunique(), "test_players": test_p.nfl_id.nunique(),
                      "train_plays": len(train_p), "test_plays": len(test_p)}
            if record["train_players"] < 12 or record["test_players"] < 5:
                results.append({**record, "status": "insufficient_sample"})
                continue
            cat = ["route_ran", "team_coverage_man_zone"]
            num = ["cushion", "down", "yards_to_go"]
            context = make_pipeline(ColumnTransformer([
                ("cat", make_pipeline(SimpleImputer(strategy="most_frequent"),
                                       OneHotEncoder(handle_unknown="ignore")), cat),
                ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), num),
            ]), Ridge(alpha=10, solver="lsqr"))
            context.fit(train_p[cat + num], train_p.separation_at_pass_forward)
            for frame in (train_p, test_p):
                frame["target"] = frame.separation_at_pass_forward - context.predict(frame[cat + num])
            train = table.merge(train_p.groupby("nfl_id").target.mean(), on="nfl_id")
            test = table.merge(test_p.groupby("nfl_id").target.mean(), on="nfl_id")
            assert set(train.nfl_id).isdisjoint(test.nfl_id)
            assert train.draft_year.max() < test.draft_year.min()
            pred = test[["nfl_id", "display_name", "draft_year", "target"]].copy()
            pred["scenario"] = scenario
            pred["mean_reference"] = train.target.mean()
            for name, columns in [("traditional", BASE), ("with_movement", BASE + EXTRA)]:
                model = numeric_model()
                model.fit(train[columns], train.target)
                pred[name] = model.predict(test[columns])
            for name in ["mean_reference", "traditional", "with_movement"]:
                record[name + "_mae"] = float((pred.target - pred[name]).abs().mean())
            delta = ((pred.target - pred.traditional).abs() - (pred.target - pred.with_movement).abs()).to_numpy()
            rng = np.random.default_rng(2027)
            boot = rng.choice(delta, size=(5000, len(delta)), replace=True).mean(axis=1)
            record.update(status="exploratory", movement_mae_improvement=float(delta.mean()),
                          ci_low=float(np.quantile(boot, .025)), ci_high=float(np.quantile(boot, .975)))
            results.append(record)
            predictions.append(pred)
    scores = pd.DataFrame(results)
    scores.to_csv(OUT / "forward_year_scores.csv", index=False)
    pd.concat(predictions).to_csv(OUT / "forward_year_predictions.csv", index=False)
    pd.DataFrame(reliability).to_csv(OUT / "outcome_reliability.csv", index=False)
    valid = scores.loc[scores.status.eq("exploratory")].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    y = np.arange(len(valid))
    ax.errorbar(valid.movement_mae_improvement, y,
                xerr=[valid.movement_mae_improvement - valid.ci_low,
                      valid.ci_high - valid.movement_mae_improvement], fmt="o", capsize=4)
    ax.axvline(0, color="gray", linestyle="--")
    ax.set_yticks(y, [f"{r.scenario} / {r.test_year} (n={r.test_players})" for r in valid.itertuples()])
    ax.set_xlabel("MAE improvement from movement features (positive is better)")
    ax.set_title("Forward-year exploratory checks; conditional 95% bootstrap intervals")
    fig.tight_layout()
    fig.savefig(OUT / "forward_year_comparison.png", dpi=150)
    plt.close(fig)
    (OUT / "design.json").write_text(json.dumps({
        "scenarios": SCENARIOS, "model": "Ridge alpha=10; no tuning", "duplicate_player_play_keys": duplicate_count,
        "validation": "train draft years strictly before test year; rookie regular season only",
        "limitations": ["Previously inspected years; not a fresh confirmatory holdout.",
                        "Six overlapping comparisons; intervals are not multiplicity-adjusted.",
                        "Bootstrap conditions on fitted models; small player samples.",
                        "HITCH is a plausible curl analogue, not an exact drill match.",
                        "Official data units remain unverified."]}, indent=2), encoding="utf-8")
    print(scores.to_string(index=False))
    print(pd.DataFrame(reliability).to_string(index=False))


if __name__ == "__main__":
    main()
