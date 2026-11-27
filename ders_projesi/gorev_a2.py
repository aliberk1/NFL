"""A2: predict snaps per season (regression) from pre-draft data. Design: TASARIM.md.

Run from the repo root:
    .venv-ml/bin/python -m ders_projesi.gorev_a2
"""
import json
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

from . import grafikler as G
from .degerlendirme import (bootstrap_ci, compare_to_reference, cv_splits, friedman,
                            metrics_reg, run_cv, summarize)
from .modeller import SkRegModel
from .ozellikler import _attempt_frames, add_dummies, tabular_feature_sets, tracking_summary
from .veri import OUT, load_players

warnings.filterwarnings("ignore", category=RuntimeWarning)  # macOS Accelerate matmul noise

OUT_DIR = OUT / "gorev_a2"
SET_LABEL = {"draft": "Draft", "combine": "Combine", "combine_trk": "Combine+Takip",
             "combine_trk_draft": "Combine+Takip+Draft"}
ALGOS = ["Ridge", "kNN", "SVR", "RandomForest", "GradBoost", "MLP"]
COLS = ("r2", "mae", "rmse", "spearman")


def main():
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_players()
    df = add_dummies(df.merge(tracking_summary(_attempt_frames()), on="nfl_id", how="left"))
    sets = tabular_feature_sets(df)
    y = df["snaps_per_season"].to_numpy(float)
    ctx = dict(X=df, y=y)

    E = {"Draft | Ortalama": lambda seed: SkRegModel("Ortalama", sets["draft"], seed)}
    for key, label in SET_LABEL.items():
        algos = ["Ridge", "GradBoost"] if key == "draft" else ALGOS
        for a in algos:
            E[f"{label} | {a}"] = (lambda a, key: lambda seed: SkRegModel(a, sets[key], seed))(a, key)

    quart = pd.qcut(pd.Series(y).rank(method="first"), 4, labels=False).to_numpy()
    strata = df["draft_year"].to_numpy() * 10 + quart
    splits = cv_splits(strata, n_splits=5, n_repeats=5)
    print(f"{len(df)} oyuncu; hedef ortalaması {y.mean():.0f} snap/sezon; "
          f"{len(E)} model × {len(splits)} katman", flush=True)

    fold_df, oof = run_cv(E, ctx, splits, metric_fn=metrics_reg, key="r2")
    summary = summarize(fold_df, cols=COLS, key="r2")
    ci = {m: bootstrap_ci(y, np.nanmean(oof[m], axis=0), metric=r2_score) for m in oof}
    summary.insert(0, "r2_ci_low", [ci[m][0] for m in summary.index])
    summary.insert(1, "r2_ci_high", [ci[m][1] for m in summary.index])
    fold_df.to_csv(OUT_DIR / "katman_metrikleri.csv", index=False)
    summary.round(4).to_csv(OUT_DIR / "ozet.csv")

    best = {}
    for label in SET_LABEL.values():
        ms = [m for m in summary.index if m.startswith(label + " |") and "Ortalama" not in m]
        best[label] = max(ms, key=lambda m: summary.loc[m, "r2_mean"])
    ref = best["Draft"]
    cmp = compare_to_reference(fold_df, oof, y, ref, key="r2", metric=r2_score)
    cmp.round(4).to_csv(OUT_DIR / "test_draft_referans.csv", index=False)
    fr = friedman(fold_df, [m for m in summary.index if "Ortalama" not in m], key="r2")
    pred = pd.DataFrame({m: np.nanmean(p, axis=0) for m, p in oof.items()})
    pred.insert(0, "nfl_id", df["nfl_id"])
    pred.insert(1, "snaps_per_season", y)
    pred.to_csv(OUT_DIR / "oof_tahminler.csv", index=False)

    G.feature_set_comparison(
        [(s, best[s], summary.loc[best[s], "r2_mean"], *ci[best[s]])
         for s in reversed(list(SET_LABEL.values()))], OUT_DIR / "ozellik_seti.png",
        xlabel="R² (OOF, %95 bootstrap güven aralığı)", xlim=(-0.1, 0.8), chance=0.0,
        chance_label="ortalama tahmini")
    G.pred_vs_actual(y, np.nanmean(oof[summary.index[0]], axis=0), OUT_DIR / "tahmin_gercek.png",
                     f"{summary.index[0]}: tahmin ve gerçek", "Tahmin edilen snap / sezon",
                     "Gerçek snap / sezon")

    h_holm = cmp.set_index("model").loc[[best[s] for s in ["Combine+Takip+Draft"]], "p_holm"].iloc[0]
    better = cmp.set_index("model").loc[best["Combine+Takip+Draft"], "r2_diff_folds"] > 0
    verdict = ("DESTEKLENDİ" if not (better and h_holm < 0.05) else "DESTEKLENMEDİ")
    md = lambda d, **k: d.to_markdown(**k)
    L = ["# A2: Sezon başına snap sayısı tahmini (regresyon)\n",
         "Bu dosya `ders_projesi/gorev_a2.py` tarafından otomatik üretilir. Tasarım: `TASARIM.md`.\n",
         f"- Oyuncu: {len(df)}; hedef = (hücum + savunma snap) / oynanabilir sezon; "
         f"ortalama {y.mean():.0f}, medyan {np.median(y):.0f}, sıfır olan {int((y == 0).sum())} oyuncu.",
         f"- 5-katlı × 5 tekrar ({len(splits)} test); ana ölçüt R².\n",
         "## Sonuçlar\n", md(summary.round(3)) + "\n", "![Özellik seti](ozellik_seti.png)\n",
         "![Tahmin ve gerçek](tahmin_gercek.png)\n",
         f"**Friedman testi:** χ² = {fr[0]:.1f}, p = {fr[1]:.2e}\n",
         f"## Hipotez H-A2\n",
         f"Referans: **{ref}**. Combine/Takip bilgisinin Draft modelinin R²'sini anlamlı biçimde "
         f"artırmayacağı öngörülmüştü. Sonuç: **{verdict}**.\n",
         md(cmp.drop(columns="reference").round(4), index=False) + "\n",
         "## Sınırlar\n",
         "- Hedef kariyer toplamlarından hesaplanır; sezonlara bölünmüş değildir.",
         "- Snap sayısının dağılımı çarpıktır (çok sayıda sıfır); R² bu yapıdan etkilenir."]
    (OUT_DIR / "RAPOR.md").write_text("\n".join(L), encoding="utf-8")
    json.dump(dict(n=int(len(df)), reference=ref, verdict=verdict, seconds=round(time.time() - t0)),
              open(OUT_DIR / "calisma.json", "w"), indent=2, ensure_ascii=False)
    print(summary[["r2_mean", "r2_std", "mae_mean", "spearman_mean"]].round(3).to_string())
    print(f"H-A2: {verdict}\nBitti: {OUT_DIR}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
