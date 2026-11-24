"""Fixed-design forward-year analysis of Combine-to-rookie route speed."""
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

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/nfl-big-data-bowl-2027"
PROCESSED = ROOT / "data/processed"
OUT = ROOT / "reports/speed_study"
BASE = ["forty", "combine_height", "combine_weight"]
SENSOR = ["combine_peak_speed", "combine_early_speed"]
CAT = ["route_ran", "team_coverage_man_zone"]
NUM = ["window_duration", "window_duration_sq", "snap_speed", "cushion"]


def player_model():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=10))


def context_model():
    return make_pipeline(ColumnTransformer([
        ("cat", make_pipeline(SimpleImputer(strategy="most_frequent"),
                               OneHotEncoder(handle_unknown="ignore")), CAT),
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), NUM),
    ]), Ridge(alpha=10, solver="lsqr"))


def errors(pred, name):
    error = pred.target - pred[name]
    return {name + "_mae": float(error.abs().mean()),
            name + "_rmse": float(np.sqrt((error ** 2).mean()))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    players = pd.read_csv(DATA / "players.csv")
    combine = pd.read_csv(DATA / "combine_results.csv")
    sensor = pd.read_csv(PROCESSED / "combine_speed_players.csv")
    plays = pd.read_csv(PROCESSED / "rookie_wr_route_speed.csv")
    counts = plays.groupby("nfl_id").size()
    table = players.merge(combine, on=["nfl_id", "draft_year"], validate="one_to_one")
    table = table.merge(sensor, on="nfl_id", validate="one_to_one")
    table = table.loc[table.nfl_position.eq("WR") & table.nfl_id.isin(counts[counts >= 30].index)].copy()
    table["valid_game_plays"] = table.nfl_id.map(counts)
    plays = plays.loc[plays.nfl_id.isin(table.nfl_id)].copy()
    assert np.isfinite(table[SENSOR].to_numpy()).all()
    assert not plays.duplicated(["game_id", "play_id", "nfl_id"]).any()
    table.to_csv(OUT / "player_features.csv", index=False)
    summary, outputs, coefficients = [], [], []
    for year in (2024, 2025):
        train_p = plays.loc[plays.draft_year.lt(year)].copy()
        test_p = plays.loc[plays.draft_year.eq(year)].copy()
        context = context_model()
        context.fit(train_p[CAT + NUM], train_p.game_peak_speed)
        for frame in (train_p, test_p):
            frame["context_prediction"] = context.predict(frame[CAT + NUM])
            frame["target"] = frame.game_peak_speed - frame.context_prediction
        train = table.merge(train_p.groupby("nfl_id").target.mean(), on="nfl_id")
        test = table.merge(test_p.groupby("nfl_id").target.mean(), on="nfl_id")
        assert train.draft_year.max() < test.draft_year.min()
        assert set(train.nfl_id).isdisjoint(test.nfl_id)
        if len(train) < 12 or len(test) < 5:
            raise ValueError(f"Insufficient primary sample for {year}: {len(train)}/{len(test)}")
        pred = test[["nfl_id", "display_name", "draft_year", "valid_game_plays", "target"]].copy()
        pred["mean_reference"] = train.target.mean()
        for label, columns in [("traditional", BASE), ("with_tracking", BASE + SENSOR)]:
            model = player_model()
            model.fit(train[columns], train.target)
            pred[label] = model.predict(test[columns])
            for feature, coefficient in zip(columns, model.named_steps["ridge"].coef_):
                coefficients.append({"test_year": year, "model": label, "feature": feature,
                                     "standardized_coefficient": coefficient})
        delta = ((pred.target - pred.traditional).abs() - (pred.target - pred.with_tracking).abs()).to_numpy()
        rng = np.random.default_rng(2027)
        boot = rng.choice(delta, size=(5000, len(delta)), replace=True).mean(axis=1)
        record = {"test_year": year, "train_players": len(train), "test_players": len(test),
                  "train_plays": len(train_p), "test_plays": len(test_p),
                  "movement_mae_improvement": float(delta.mean()),
                  "ci_low": float(np.quantile(boot, .025)), "ci_high": float(np.quantile(boot, .975)),
                  "context_play_test_mae": float((test_p.game_peak_speed - test_p.context_prediction).abs().mean())}
        for name in ["mean_reference", "traditional", "with_tracking"]:
            record.update(errors(pred, name))
        summary.append(record)
        outputs.append(pred)
    predictions = pd.concat(outputs, ignore_index=True)
    scores = pd.DataFrame(summary)
    scores.to_csv(OUT / "forward_year_scores.csv", index=False)
    predictions.to_csv(OUT / "forward_year_predictions.csv", index=False)
    pd.DataFrame(coefficients).to_csv(OUT / "model_coefficients.csv", index=False)

    # Descriptive repeatability across disjoint alternating games.
    game_order = plays[["nfl_id", "game_id"]].drop_duplicates().sort_values(["nfl_id", "game_id"])
    game_order["half"] = game_order.groupby("nfl_id").cumcount() % 2
    split = plays.merge(game_order, on=["nfl_id", "game_id"], validate="many_to_one")
    halves = split.groupby(["nfl_id", "half"]).game_peak_speed.agg(["mean", "size"]).unstack()
    eligible = halves["size"].ge(10).all(axis=1)
    means = halves.loc[eligible, "mean"]
    game_reliability = float(means[0].corr(means[1]))
    means.to_csv(OUT / "game_split_half_means.csv")
    attempts = pd.read_csv(PROCESSED / "combine_speed_attempts.csv").sort_values(["nfl_id", "attempt", "event_id"])
    attempts["repeat_index"] = attempts.groupby("nfl_id").cumcount()
    repeats = attempts.loc[attempts.repeat_index.lt(2)].pivot(index="nfl_id", columns="repeat_index", values=SENSOR)
    repeat_corr = {column: float(repeats[column][0].corr(repeats[column][1])) for column in SENSOR}
    raw = table.merge(plays.groupby("nfl_id").game_peak_speed.mean(), on="nfl_id")
    raw.to_csv(OUT / "descriptive_player_means.csv", index=False)
    corr = raw[BASE + SENSOR + ["game_peak_speed"]].corr()
    corr.to_csv(OUT / "descriptive_correlations.csv")
    info = {"status": "exploratory", "primary_players": len(table), "primary_plays": len(plays),
            "players_by_year": {str(k): int(v) for k, v in table.groupby("draft_year").size().items()},
            "missing_classic_features": table[BASE].isna().sum().to_dict(),
            "game_split_half_players": int(eligible.sum()), "game_split_half_correlation": game_reliability,
            "combine_repeat_correlations": repeat_corr,
            "combine_players_with_two_attempts": int(repeats[SENSOR[0]].dropna().shape[0]),
            "raw_peak_game_correlation": float(corr.loc["combine_peak_speed", "game_peak_speed"]),
            "scores": summary,
            "limitations": ["Route speed is not overall football success or receiver separation.",
                            "All analyses exploratory; earlier outcomes from these years were inspected.",
                            "Bootstrap is conditional on fitted folds and ignores training uncertainty.",
                            "Only participating Combine players and observed rookie pass routes are included.",
                            "Pre-throw window restriction selects longer-developing pass plays.",
                            "Additive context model does not remove all team, route depth, or tactical effects.",
                            "Official speed units are not yet verified."]}
    (OUT / "summary.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for year, group in raw.groupby("draft_year"):
        axes[0].scatter(group.combine_peak_speed, group.game_peak_speed, label=str(year), alpha=.8)
    axes[0].set(xlabel="Combine 40-yard tracking peak speed", ylabel="Mean rookie pre-throw route peak speed",
                title="Descriptive association (not context adjusted)")
    axes[0].legend(title="Draft year")
    x = np.arange(len(scores))
    for i, (name, label) in enumerate([("mean_reference", "Mean"), ("traditional", "Classic"),
                                      ("with_tracking", "Classic + tracking")]):
        axes[1].bar(x + (i - 1) * .25, scores[name + "_mae"], width=.25, label=label)
    axes[1].set(xticks=x, xticklabels=scores.test_year.astype(str), ylabel="Player MAE (lower is better)",
                title="Forward-year, context-adjusted prediction")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "speed_transfer_results.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(means[0], means[1], alpha=.7)
    ax.set(xlabel="Mean speed: alternating games, half 1", ylabel="Mean speed: alternating games, half 2",
           title=f"Raw outcome stability: r={game_reliability:.2f}, n={len(means)}")
    fig.tight_layout()
    fig.savefig(OUT / "game_speed_reliability.png", dpi=160)
    plt.close(fig)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
