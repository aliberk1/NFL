"""Exploratory WR pilot; all outcome adjustment is fitted inside held-out-year folds."""
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
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/nfl-big-data-bowl-2027"
OUT = ROOT / "reports/wr_pilot"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ["forty", "combine_height", "combine_weight"]
EXTRA = ["entry_speed", "turn_speed_ratio", "exit_speed_ratio"]


def numeric_model():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=10))


def main():
    players = pd.read_csv(DATA / "players.csv")
    wr = players.loc[players.nfl_position.eq("WR")]
    tracking = pd.read_csv(DATA / "combine_tracking.csv")
    tracking = tracking.loc[tracking.entity_type.eq("PLAYER") &
                            tracking.nfl_id.isin(wr.nfl_id) &
                            tracking.drill_name.eq("CURL_ROUTE_RIGHT")].copy()
    tracking["time"] = pd.to_datetime(tracking.time)
    features, rejected, examples = [], [], []
    for key, g in tracking.groupby(["nfl_id", "event_id", "attempt"]):
        g = g.sort_values("time").drop_duplicates("time")
        t = (g.time - g.time.iloc[0]).dt.total_seconds().to_numpy()
        xy = g[["x", "y"]].to_numpy()
        speed = g.s.rolling(3, center=True, min_periods=1).median().to_numpy()
        # Estimate the outward stem from the first substantial displacement.
        distance = np.linalg.norm(xy - xy[0], axis=1)
        stem_candidates = np.flatnonzero(distance >= 5)
        reason = None
        if len(t) < 20 or not len(stem_candidates):
            reason = "short_record_or_stem"
        elif np.max(np.diff(t)) > 0.21:
            reason = "time_gap"
        if reason:
            rejected.append({"nfl_id": key[0], "event_id": key[1], "reason": reason})
            continue
        stem = xy[stem_candidates[0]] - xy[0]
        stem /= np.linalg.norm(stem)
        progress = (xy - xy[0]) @ stem
        # Use the first sustained reversal; the post-catch run can exceed the stem.
        candidates = [i for i in range(1, len(t) - 5)
                      if progress[i] >= 5 and progress[i] >= progress[i - 1]
                      and progress[i + 1] <= progress[i]
                      and progress[i] - progress[i + 5] >= 0.3]
        if not candidates:
            rejected.append({"nfl_id": key[0], "event_id": key[1], "reason": "no_stem_reversal"})
            continue
        turn = candidates[0]
        bt = t[turn]
        pre = (t >= bt - 1.5) & (t <= bt - 0.5)
        near = np.abs(t - bt) <= 0.3
        post = (t >= bt + 0.4) & (t <= bt + 0.8)
        if (not pre.any() or not post.any() or progress[turn] < 5 or
                speed[pre].max() < 2):
            rejected.append({"nfl_id": key[0], "event_id": key[1], "reason": "unresolved_turn"})
            continue
        entry = speed[pre].max()
        features.append({"nfl_id": key[0], "event_id": key[1], "attempt": key[2],
                         "entry_speed": entry, "turn_speed_ratio": speed[near].min() / entry,
                         "exit_speed_ratio": speed[post].mean() / entry})
        if len(examples) < 9:
            examples.append((key[0], xy, turn))
    attempts = pd.DataFrame(features)
    attempts.to_csv(OUT / "combine_attempt_features.csv", index=False)
    pd.DataFrame(rejected).to_csv(OUT / "rejected_attempts.csv", index=False)
    feature = attempts.groupby("nfl_id")[EXTRA].median().reset_index()
    table = wr.merge(pd.read_csv(DATA / "combine_results.csv"), on=["nfl_id", "draft_year"])
    table = table.merge(feature, on="nfl_id")

    games = pd.read_csv(DATA / "games.csv")
    cols = ["game_id", "play_id", "nfl_id", "route_ran", "separation_at_pass_forward",
            "team_coverage_man_zone", "cushion", "down", "yards_to_go", "play_nullified_by_penalty"]
    plays = pd.read_csv(DATA / "player_play.csv", usecols=cols)
    plays = plays.merge(games[["game_id", "season", "season_type"]], on="game_id")
    plays = plays.merge(wr[["nfl_id", "draft_year"]], on="nfl_id")
    # Comparable exposure: rookie regular season only, with valid route/target measurement.
    plays = plays.loc[plays.season_type.eq("REG") & plays.season.eq(plays.draft_year) &
                      plays.play_nullified_by_penalty.eq("N") &
                      plays.separation_at_pass_forward.notna() & plays.route_ran.notna()].copy()
    counts = plays.groupby("nfl_id").size()
    eligible = counts[counts >= 30].index
    table = table.loc[table.nfl_id.isin(eligible)].copy()
    plays = plays.loc[plays.nfl_id.isin(table.nfl_id)].copy()
    table["rookie_plays"] = table.nfl_id.map(counts)
    table.to_csv(OUT / "player_features.csv", index=False)
    predictions, folds = [], []
    cat = ["route_ran", "team_coverage_man_zone"]
    num = ["cushion", "down", "yards_to_go"]
    for year in sorted(table.draft_year.unique()):
        train_p = plays.loc[plays.draft_year.ne(year)].copy()
        test_p = plays.loc[plays.draft_year.eq(year)].copy()
        preprocess = ColumnTransformer([
            ("cat", make_pipeline(SimpleImputer(strategy="most_frequent"),
                                   OneHotEncoder(handle_unknown="ignore")), cat),
            ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), num),
        ])
        context = make_pipeline(preprocess, Ridge(alpha=10, solver="lsqr"))
        context.fit(train_p[cat + num], train_p.separation_at_pass_forward)
        for frame in (train_p, test_p):
            frame["adjusted_separation"] = frame.separation_at_pass_forward - context.predict(frame[cat + num])
        train = table.merge(train_p.groupby("nfl_id").adjusted_separation.mean(), on="nfl_id")
        test = table.merge(test_p.groupby("nfl_id").adjusted_separation.mean(), on="nfl_id")
        result = test[["nfl_id", "display_name", "draft_year", "rookie_plays", "adjusted_separation"]].copy()
        result["mean_reference"] = train.adjusted_separation.mean()
        for label, columns in [("traditional", BASE), ("with_movement", BASE + EXTRA)]:
            model = numeric_model()
            model.fit(train[columns], train.adjusted_separation)
            result[label] = model.predict(test[columns])
        predictions.append(result)
        folds.append({"held_out_year": int(year), "train_players": len(train), "test_players": len(test)})
    pred = pd.concat(predictions, ignore_index=True)
    pred.to_csv(OUT / "held_out_predictions.csv", index=False)
    scores = {name: {"MAE": mean_absolute_error(pred.adjusted_separation, pred[name]),
                     "RMSE": float(np.sqrt(mean_squared_error(pred.adjusted_separation, pred[name])))}
              for name in ["mean_reference", "traditional", "with_movement"]}
    delta = (pred.adjusted_separation - pred.traditional).abs().to_numpy() - (
        pred.adjusted_separation - pred.with_movement).abs().to_numpy()
    rng = np.random.default_rng(2027)
    boot = np.array([rng.choice(delta, size=len(delta), replace=True).mean() for _ in range(5000)])
    summary = {"status": "exploratory; turn detector requires visual review; no tuning performed",
               "curl_players": int(tracking.nfl_id.nunique()), "accepted_attempts": len(attempts),
               "rejected_attempts": len(rejected), "players_with_features": len(feature),
               "model_players": len(table), "rookie_play_rows": len(plays), "folds": folds,
               "scores": scores, "movement_MAE_improvement": float(delta.mean()),
               "paired_player_bootstrap_95_interval": np.quantile(boot, [.025, .975]).tolist(),
               "caveats": ["Bootstrap conditions on fitted folds and is not full training uncertainty.",
                           "Separation at pass release is contextual, not a causal measure of skill.",
                           "Only observed rookie routes and Combine participants are represented.",
                           "Tracking speed units must be confirmed from the official data dictionary."]}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    fig, axes = plt.subplots(3, 3, figsize=(11, 10))
    for ax, (pid, xy, turn) in zip(axes.flat, examples):
        ax.plot(xy[:, 0], xy[:, 1], "-", linewidth=2)
        ax.scatter(*xy[0], color="green", label="Start")
        ax.scatter(*xy[turn], color="red", label="Detected turn")
        ax.set_title(wr.set_index("nfl_id").loc[pid, "display_name"])
        ax.set_aspect("equal", adjustable="datalim")
    axes.flat[0].legend(fontsize=8)
    fig.suptitle("Curl-route turn detection: exploratory quality check")
    fig.tight_layout()
    fig.savefig(OUT / "turn_detection.png", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(["Mean only", "Traditional", "+ Movement"], [scores[k]["MAE"] for k in scores])
    ax.set_ylabel("Held-out player MAE (separation units; lower is better)")
    ax.set_title(f"Rookie separation pilot: {len(pred)} WRs, held-out draft years")
    fig.tight_layout()
    fig.savefig(OUT / "model_comparison.png", dpi=150)
    plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
