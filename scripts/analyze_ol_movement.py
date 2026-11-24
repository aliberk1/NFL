"""Follow-up construct validation: mirror lateral motion to early game motion."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline

from analyze_mirror_protection import CLASSIC, player_model, preprocessing

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/trenches"


def main():
    table = pd.read_csv(OUT / "mirror_model_players.csv")
    plays = pd.read_csv(OUT / "ol_early_movement.csv", low_memory=False)
    counts = plays.groupby("nfl_id").size()
    table = table.loc[table.nfl_id.isin(counts[counts >= 50].index)].copy()
    plays = plays.loc[plays.nfl_id.isin(table.nfl_id)].copy()
    table["movement_plays"] = table.nfl_id.map(counts)
    table.to_csv(OUT / "movement_model_players.csv", index=False)
    scores, predictions = [], []
    numeric = ["down", "yards_to_go", "snap_speed"]
    categorical = ["lined_up_position", "offense_formation"]
    for year in (2024, 2025):
        train_p, test_p = plays.loc[plays.draft_year.lt(year)].copy(), plays.loc[plays.draft_year.eq(year)].copy()
        context = make_pipeline(preprocessing(numeric, categorical), Ridge(alpha=10, solver="lsqr"))
        context.fit(train_p[numeric + categorical], train_p.game_lateral_speed_p75)
        for frame in (train_p, test_p):
            frame["target"] = frame.game_lateral_speed_p75 - context.predict(frame[numeric + categorical])
        train = table.merge(train_p.groupby("nfl_id").target.mean(), on="nfl_id")
        test = table.merge(test_p.groupby("nfl_id").target.mean(), on="nfl_id")
        assert set(train.nfl_id).isdisjoint(test.nfl_id)
        assert train.draft_year.max() < test.draft_year.min()
        pred = test[["nfl_id", "display_name", "draft_year", "nfl_position", "movement_plays", "target"]].copy()
        pred["mean_reference"] = train.target.mean()
        for name, columns in [("classic", CLASSIC), ("whole_drill", CLASSIC + ["whole_drill_speed"]),
                              ("mirror_lateral", CLASSIC + ["lateral_speed_p75"])]:
            model = player_model(columns).fit(train[columns + ["nfl_position"]], train.target)
            pred[name] = model.predict(test[columns + ["nfl_position"]])
        predictions.append(pred)
        for name in ["mean_reference", "classic", "whole_drill", "mirror_lateral"]:
            error = pred.target - pred[name]
            delta = (pred.target - pred["classic"]).abs().to_numpy() - error.abs().to_numpy()
            rng = np.random.default_rng(2027)
            boot = rng.choice(delta, size=(5000, len(delta)), replace=True).mean(axis=1)
            scores.append({"test_year": year, "model": name, "train_players": len(train), "test_players": len(test),
                           "train_plays": len(train_p), "test_plays": len(test_p),
                           "mae": float(error.abs().mean()), "rmse": float(np.sqrt(np.mean(error ** 2))),
                           "improvement_over_classic": float(delta.mean()),
                           "ci_low": float(np.quantile(boot, .025)), "ci_high": float(np.quantile(boot, .975))})
    scores = pd.DataFrame(scores)
    scores.to_csv(OUT / "movement_forward_year_scores.csv", index=False)
    pd.concat(predictions, ignore_index=True).to_csv(OUT / "movement_predictions.csv", index=False)
    raw = table.merge(plays.groupby("nfl_id").game_lateral_speed_p75.mean(), on="nfl_id")
    raw.to_csv(OUT / "movement_player_means.csv", index=False)
    cols = ["lateral_speed_p75", "game_lateral_speed_p75", "whole_drill_speed"]
    demeaned = raw[cols] - raw.groupby(["draft_year", "nfl_position"])[cols].transform("mean")
    correlations = []
    for name, frame in [("pooled", raw)] + [(str(y), g) for y, g in raw.groupby("draft_year")] + [
            ("within_year_position", demeaned)]:
        correlations.append({"group": name, "players": len(frame),
                             "mirror_vs_game": float(frame.lateral_speed_p75.corr(frame.game_lateral_speed_p75)),
                             "whole_drill_vs_game": float(frame.whole_drill_speed.corr(frame.game_lateral_speed_p75))})
    pd.DataFrame(correlations).to_csv(OUT / "movement_correlations.csv", index=False)
    game_order = plays[["nfl_id", "game_id"]].drop_duplicates().sort_values(["nfl_id", "game_id"])
    game_order["half"] = game_order.groupby("nfl_id").cumcount() % 2
    split = plays.merge(game_order, on=["nfl_id", "game_id"], validate="many_to_one")
    halves = split.groupby(["nfl_id", "half"]).game_lateral_speed_p75.agg(["mean", "size"]).unstack()
    half_eligible = halves["size"].ge(20).all(axis=1)
    means = halves.loc[half_eligible, "mean"]
    summary = {"status": "follow-up exploratory construct validation; pressure result remains the primary outcome",
               "players": len(table), "plays": len(plays), "game_split_half_players": len(means),
               "game_split_half_correlation": float(means[0].corr(means[1])),
               "correlations": correlations, "scores": scores.to_dict("records"),
               "limitations": ["Early lateral movement reflects assignment and opponent response, not necessarily superior skill.",
                               "One Combine mirror attempt per player; coach instruction is unobserved.",
                               "This follow-up was specified after the pressure outcome analysis.",
                               "Within-year/position demeaning is descriptive, not independent validation."]}
    (OUT / "movement_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    pos_colors = {"T": "#176b87", "G": "#e07a2b", "C": "#2e8b57"}
    for position, group in raw.groupby("nfl_position"):
        axes[0].scatter(group.lateral_speed_p75, group.game_lateral_speed_p75,
                        label=position, color=pos_colors.get(position, "#334455"), s=42, alpha=.85, edgecolor="white", linewidth=0.5)
    axes[0].set(xlabel="Combine Mirror Lateral Speed, 75th Percentile (yd/s)",
                ylabel="Mean Rookie Early-Game Lateral Speed, 0–1.5 s (yd/s)",
                title="A. Same Axis, Different Tasks (Pooled r = +0.053, Demeaned r = +0.120)")
    axes[0].grid(linestyle=":", alpha=0.45)
    axes[0].spines["top"].set_visible(False)
    axes[0].spines["right"].set_visible(False)
    axes[0].legend(title="Position", frameon=True, fontsize=8.5)
    palette = [("classic", "Classic Combine", "#4a6fe3"),
               ("whole_drill", "+ Whole-Drill Speed", "#e07a2b"),
               ("mirror_lateral", "+ Mirror Lateral Speed", "#176b87")]
    for i, (name, label, color) in enumerate(palette):
        rows = scores.loc[scores.model.eq(name)].sort_values("test_year")
        xpos = np.arange(2) + (i - 1) * .25
        bars = axes[1].bar(xpos, rows.mae, width=.24, label=label, color=color, edgecolor="white", linewidth=0.7)
        for bar, val in zip(bars, rows.mae):
            axes[1].text(bar.get_x() + bar.get_width() / 2, val + 0.002, f"{val:.3f}",
                         ha="center", va="bottom", fontsize=8, color="#1f2d3d", fontweight="semibold")
    axes[1].set(xticks=[0, 1], xticklabels=["2024 Rookie Class\n(Train: 17, Test: 16)", "2025 Rookie Class\n(Train: 33, Test: 17)"],
                ylabel="Out-of-Time Player MAE (yd/s; lower is better)",
                title="B. Forward-Year Early-Game Lateral Speed Prediction")
    axes[1].set_ylim(0, max(scores.mae) * 1.22)
    axes[1].grid(axis="y", linestyle=":", alpha=0.45)
    axes[1].spines["top"].set_visible(False)
    axes[1].spines["right"].set_visible(False)
    axes[1].legend(fontsize=8.5, frameon=True)
    fig.tight_layout()
    fig.savefig(OUT / "movement_bridge_results.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
