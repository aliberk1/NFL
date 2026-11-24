"""Fixed-design mirror phase features versus rookie one-on-one pressure allowed."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/nfl-big-data-bowl-2027"
OUT = ROOT / "reports/trenches"
CLASSIC = ["forty", "ten_yd_split", "combine_weight", "arm_length"]
MIRROR = ["lateral_speed_p75", "reversal_recovery"]


def preprocessing(numeric, categorical):
    return ColumnTransformer([
        ("numeric", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), numeric),
        ("categorical", make_pipeline(SimpleImputer(strategy="most_frequent"),
                                      OneHotEncoder(handle_unknown="ignore")), categorical),
    ])


def player_model(numeric):
    return make_pipeline(preprocessing(numeric, ["nfl_position"]), Ridge(alpha=10, solver="lsqr"))


def load_data():
    players = pd.read_csv(DATA / "players.csv")
    table = players.merge(pd.read_csv(DATA / "combine_results.csv"), on=["nfl_id", "draft_year"], validate="one_to_one")
    table = table.merge(pd.read_csv(OUT / "mirror_player_features.csv"), on="nfl_id", validate="one_to_one")
    plays = pd.read_csv(OUT / "ol_rookie_plays.csv", low_memory=False)
    plays = plays.loc[plays.lined_up_position.isin(["T", "G", "C"]) & plays.pressure_allowed.notna() &
                      plays.pass_rushers_encountered.eq(1)].copy()
    plays["pressure"] = plays.pressure_allowed.map({True: 1, False: 0, "True": 1, "False": 0})
    plays["pressure_prob"] = pd.to_numeric(plays.peak_pressure_probability_allowed, errors="coerce")
    assert plays.pressure.notna().all() and plays.pressure_prob.notna().all()
    plays["duration_sq"] = plays.dropback_duration ** 2
    count = plays.groupby("nfl_id").size()
    table = table.loc[table.nfl_id.isin(count[count >= 100].index)].copy()
    table["opportunities"] = table.nfl_id.map(count)
    plays = plays.loc[plays.nfl_id.isin(table.nfl_id)].copy()
    return table, plays


def main():
    table, plays = load_data()
    assert not plays.duplicated(["game_id", "play_id", "nfl_id"]).any()
    table.to_csv(OUT / "mirror_model_players.csv", index=False)
    scores, predictions, context_checks = [], [], []
    categorical = ["lined_up_position", "offense_formation"]
    variants = [
        "primary_with_duration",
        "sensitivity_without_duration",
        "continuous_pressure_probability",
    ]
    for variant in variants:
        numeric = ["down", "yards_to_go"]
        if variant != "sensitivity_without_duration":
            numeric += ["dropback_duration", "duration_sq"]
        for year in (2024, 2025):
            train_p = plays.loc[plays.draft_year.lt(year)].copy()
            test_p = plays.loc[plays.draft_year.eq(year)].copy()
            if variant == "continuous_pressure_probability":
                context = make_pipeline(preprocessing(numeric, categorical), Ridge(alpha=10, solver="lsqr"))
                context.fit(train_p[numeric + categorical], 100 * train_p.pressure_prob)
                for frame in (train_p, test_p):
                    frame["expected"] = np.clip(context.predict(frame[numeric + categorical]) / 100.0, 0.0, 1.0)
                    frame["target"] = 100 * (frame.pressure_prob - frame.expected)
                obs_col = "pressure_prob"
                brier_val = float(np.mean((test_p.pressure_prob - test_p.expected) ** 2))
            else:
                context = make_pipeline(preprocessing(numeric, categorical), LogisticRegression(C=1, max_iter=2000))
                context.fit(train_p[numeric + categorical], train_p.pressure)
                for frame in (train_p, test_p):
                    frame["expected"] = context.predict_proba(frame[numeric + categorical])[:, 1]
                    frame["target"] = 100 * (frame.pressure - frame.expected)
                obs_col = "pressure"
                brier_val = float(brier_score_loss(test_p.pressure, test_p.expected))
            train = table.merge(train_p.groupby("nfl_id").target.mean(), on="nfl_id")
            test = table.merge(test_p.groupby("nfl_id").target.mean(), on="nfl_id")
            assert set(train.nfl_id).isdisjoint(test.nfl_id)
            assert train.draft_year.max() < test.draft_year.min()
            assert len(train) >= 12 and len(test) >= 5
            pred = test[["nfl_id", "display_name", "draft_year", "nfl_position", "opportunities", "target"]].copy()
            pred["variant"] = variant
            pred["mean_reference"] = train.target.mean()
            models = [("classic", CLASSIC), ("whole_drill", CLASSIC + ["whole_drill_speed"]),
                      ("mirror_phase", CLASSIC + MIRROR)]
            for name, columns in models:
                model = player_model(columns)
                model.fit(train[columns + ["nfl_position"]], train.target)
                pred[name] = model.predict(test[columns + ["nfl_position"]])
            predictions.append(pred)
            for name in ["mean_reference", "classic", "whole_drill", "mirror_phase"]:
                error = pred.target - pred[name]
                delta = (pred.target - pred["classic"]).abs().to_numpy() - error.abs().to_numpy()
                rng = np.random.default_rng(2027)
                bootstrap = rng.choice(delta, size=(5000, len(delta)), replace=True).mean(axis=1)
                scores.append({"variant": variant, "test_year": year, "model": name,
                               "train_players": len(train), "test_players": len(test),
                               "train_plays": len(train_p), "test_plays": len(test_p),
                               "mae_pp": float(error.abs().mean()), "rmse_pp": float(np.sqrt((error ** 2).mean())),
                               "improvement_over_classic_pp": float(delta.mean()),
                               "ci_low": float(np.quantile(bootstrap, .025)), "ci_high": float(np.quantile(bootstrap, .975))})
            context_checks.append({"variant": variant, "test_year": year,
                                   "observed_rate": float(test_p[obs_col].mean()),
                                   "predicted_rate": float(test_p.expected.mean()),
                                   "brier": brier_val})
    result = pd.DataFrame(scores)
    result.to_csv(OUT / "mirror_forward_year_scores.csv", index=False)
    pd.concat(predictions, ignore_index=True).to_csv(OUT / "mirror_predictions.csv", index=False)
    pd.DataFrame(context_checks).to_csv(OUT / "mirror_context_checks.csv", index=False)
    game_keys = plays[["nfl_id", "game_id"]].drop_duplicates().sort_values(["nfl_id", "game_id"])
    game_keys["half"] = game_keys.groupby("nfl_id").cumcount() % 2
    split = plays.merge(game_keys, on=["nfl_id", "game_id"], validate="many_to_one")
    halves = split.groupby(["nfl_id", "half"]).pressure.agg(["mean", "size"]).unstack()
    half_eligible = halves["size"].ge(20).all(axis=1)
    stability = halves.loc[half_eligible, "mean"]
    halves_prob = split.groupby(["nfl_id", "half"]).pressure_prob.agg(["mean", "size"]).unstack()
    stability_prob = halves_prob.loc[half_eligible, "mean"]
    summary = {"status": "exploratory research; not a finalized competition entry",
               "players": len(table), "plays": len(plays), "pressures": int(plays.pressure.sum()),
               "players_by_year": table.groupby("draft_year").size().to_dict(),
               "classic_missing": table[CLASSIC].isna().sum().to_dict(),
               "raw_game_split_half_players": len(stability),
               "raw_game_split_half_correlation": float(stability[0].corr(stability[1])),
               "continuous_pressure_prob_split_half_correlation": float(stability_prob[0].corr(stability_prob[1])),
               "scores": scores, "limitations": [
                   "One mirror attempt per player; boundary robustness is not repeatability.",
                   "Small cohorts and multiple research questions across the project.",
                   "Pressure labels and dropback duration are supplied game outcomes; context adjustment is not causal.",
                   "Conditional bootstrap excludes training uncertainty.",
                   "Mirror phase includes the transition into exit until the geometric threshold is crossed.",
                   "The drill is coach-directed; faster movement can reflect different instructions."]}
    (OUT / "mirror_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.8))
    panel_specs = [
        ("primary_with_duration", "A. Primary: Binary Pressure\n(Duration-Adjusted Residual, pp)"),
        ("sensitivity_without_duration", "B. Sensitivity: Binary Pressure\n(No Dropback-Duration Adjustment, pp)"),
        ("continuous_pressure_probability", "C. Continuous Sensitivity:\nPeak Pressure Probability (pp)"),
    ]
    palette = [("classic", "Classic Combine", "#4a6fe3"),
               ("whole_drill", "+ Whole-Drill Speed (Exit)", "#e07a2b"),
               ("mirror_phase", "+ Mirror-Phase Features", "#176b87")]
    for ax, (variant, title) in zip(axes, panel_specs):
        selection = result.loc[result.variant.eq(variant)]
        for i, (name, label, color) in enumerate(palette):
            rows = selection.loc[selection.model.eq(name)].sort_values("test_year")
            xpos = np.arange(2) + (i - 1) * .25
            bars = ax.bar(xpos, rows.mae_pp, width=.24, label=label, color=color, edgecolor="white", linewidth=0.7)
            for bar, val in zip(bars, rows.mae_pp):
                ax.text(bar.get_x() + bar.get_width() / 2, val + 0.03, f"{val:.2f}",
                        ha="center", va="bottom", fontsize=7.5, color="#1f2d3d", fontweight="semibold")
        mean_ref = selection.loc[selection.model.eq("mean_reference")].sort_values("test_year")
        for idx_yr, ref_val in enumerate(mean_ref.mae_pp):
            ax.hlines(ref_val, idx_yr - 0.38, idx_yr + 0.38, colors="#7f8c8d", linestyles="--", linewidth=1.2,
                      label="Training Mean Reference" if idx_yr == 0 else None)
        ax.set_xticks([0, 1], ["2024 Rookie Class\n(Train: 17, Test: 16)", "2025 Rookie Class\n(Train: 33, Test: 17)"])
        ax.set_title(title, fontsize=10.5, fontweight="bold", pad=8)
        ax.set_ylim(0, max(selection.mae_pp) * 1.22)
        ax.grid(axis="y", linestyle=":", alpha=0.45)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].set_ylabel("Out-of-Time Player MAE (percentage points; lower is better)", fontsize=9.5)
    axes[0].legend(fontsize=8, loc="upper left", frameon=True)
    fig.suptitle("Forward-Year One-on-One Pass-Protection Prediction Across Outcome Specifications (50 OL, 20,853 Snaps)",
                 fontsize=12.5, fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig(OUT / "mirror_model_comparison.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(result.to_string(index=False))
    print(json.dumps({key: val for key, val in summary.items() if key != "scores"}, indent=2))


if __name__ == "__main__":
    main()
