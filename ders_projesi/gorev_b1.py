"""B1: does a player's rookie season predict how much he plays the next season? Design: TASARIM.md.

Run from the repo root:
    .venv-ml/bin/python -m ders_projesi.gorev_b1
"""
import json
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from . import grafikler as G
from .degerlendirme import (bootstrap_ci, compare_to_reference, cv_splits, friedman, metrics,
                            run_cv, summarize)
from .modeller import SkModel
from .ozellikler import _attempt_frames, add_dummies, tabular_feature_sets, tracking_summary
from .sezon import ROOKIE_COLS, season_table
from .veri import OUT, load_players

warnings.filterwarnings("ignore", category=RuntimeWarning)  # macOS Accelerate matmul noise

OUT_DIR = OUT / "gorev_b1"
TOP_SHARE = 0.25
ALGOS = ["LogReg", "kNN", "SVM", "RandomForest", "GradBoost", "MLP"]
SET_ORDER = ["Draft", "Çaylak", "Draft+Çaylak", "Draft+Çaylak+Combine"]
G.SET_COLORS.update({"Çaylak": G.SET_COLORS["Combine+Takip"],
                     "Draft+Çaylak": G.SET_COLORS["Combine+Takip+Draft"],
                     "Draft+Çaylak+Combine": G.SET_COLORS["Combine"]})


def build():
    df = load_players()
    df = add_dummies(df.merge(tracking_summary(_attempt_frames()), on="nfl_id", how="left"))
    st = season_table()
    rookie = st.rename(columns={c: f"rk_{c}" for c in ROOKIE_COLS})
    df = df.merge(rookie[["nfl_id", "season"] + [f"rk_{c}" for c in ROOKIE_COLS]],
                  left_on=["nfl_id", "draft_year"], right_on=["nfl_id", "season"], how="left")
    # No regular-season row in the rookie year = did not play: counts are 0, rates stay missing.
    for c in ["snaps", "games", "targets", "routes", "rec_yards", "rush_yards", "sacks", "tackles",
              "trk_plays", "snaps_per_game"]:
        df[f"rk_{c}"] = df[f"rk_{c}"].fillna(0)
    nxt = st[["nfl_id", "season", "snaps"]].rename(columns={"snaps": "next_snaps"})
    nxt["season"] = nxt["season"] - 1
    df = df.merge(nxt, left_on=["nfl_id", "draft_year"], right_on=["nfl_id", "season"],
                  how="left", suffixes=("", "_n")).drop(columns=["season", "season_n"])
    df["next_snaps"] = df["next_snaps"].fillna(0)
    known = df["draft_year"] < 2025
    pct = df[known].groupby(["draft_year", "position_group"])["next_snaps"].rank(pct=True, method="max")
    df.loc[known, "y_next_top"] = ((pct > 1 - TOP_SHARE) & (df.loc[known, "next_snaps"] > 0)
                                   & (df.loc[known, "position_group"] != "OTHER")).astype(int)
    return df


def feature_sets(df):
    base = tabular_feature_sets(df)
    draft = base["draft"]
    pos = [f"pos_{g}" for g in ["OL", "DL", "LB", "DB", "WR", "TE"]]
    rookie = [f"rk_{c}" for c in ROOKIE_COLS] + pos
    combine = [c for c in base["combine_trk"] if not c.startswith("cohort_") and c not in pos]
    return {"Draft": draft + pos, "Çaylak": rookie, "Draft+Çaylak": draft + rookie,
            "Draft+Çaylak+Combine": draft + rookie + combine}


def experiments(sets):
    E = {}
    for label in SET_ORDER:
        for a in (["LogReg", "GradBoost"] if label == "Draft" else ALGOS):
            E[f"{label} | {a}"] = (lambda a, label: lambda seed: SkModel(a, sets[label], seed))(a, label)
    return E


def main():
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = build()
    sets = feature_sets(df)
    E = experiments(sets)
    data = df[df["draft_year"] < 2025].reset_index(drop=True)
    y = data["y_next_top"].astype(int).to_numpy()
    ctx = dict(X=data, y=y)
    cohort = data["draft_year"].to_numpy()
    print(f"{len(data)} oyuncu (2023+2024 sınıfları), {y.sum()} pozitif; {len(E)} model", flush=True)

    # ---- 1. repeated CV
    splits = cv_splits(y * 10000 + cohort, n_splits=5, n_repeats=5)
    fold_df, oof = run_cv(E, ctx, splits)
    summary = summarize(fold_df)
    ci = {m: bootstrap_ci(y, np.nanmean(oof[m], axis=0)) for m in oof}
    summary.insert(0, "auc_ci_low", [ci[m][0] for m in summary.index])
    summary.insert(1, "auc_ci_high", [ci[m][1] for m in summary.index])
    best = {s: max([m for m in summary.index if m.startswith(s + " |")],
                   key=lambda m: summary.loc[m, "auc_mean"]) for s in SET_ORDER}
    ref = best["Draft"]
    cmp = compare_to_reference(fold_df, oof, y, ref)
    fr = friedman(fold_df, list(summary.index))
    fold_df.to_csv(OUT_DIR / "katman_metrikleri.csv", index=False)
    summary.round(4).to_csv(OUT_DIR / "ozet.csv")
    cmp.round(4).to_csv(OUT_DIR / "test_draft_referans.csv", index=False)

    # ---- 2. time test: train 2023 class, test 2024 class
    tr, te = np.where(cohort == 2023)[0], np.where(cohort == 2024)[0]
    time_rows = [dict(model=best[s], **metrics(y[te], E[best[s]](seed=0).fit(ctx, tr).predict(ctx, te)))
                 for s in SET_ORDER]
    time_test = pd.DataFrame(time_rows)
    time_test.round(4).to_csv(OUT_DIR / "zaman_testi.csv", index=False)

    # ---- 3. forecast: fit on 2023+2024, predict 2025 class (rookie 2025 -> 2026, unknown)
    chosen = summary.index[0]
    fut = df[df["draft_year"] == 2025].reset_index(drop=True)
    allx = pd.concat([data, fut], ignore_index=True)
    actx = dict(X=allx, y=np.concatenate([y, np.zeros(len(fut), int)]))
    fut_idx = np.arange(len(data), len(allx))
    fc = fut[["nfl_id", "display_name", "nfl_position", "position_group", "draft_overall_pick",
              "rk_snaps", "rk_games"]].copy()
    for m in dict.fromkeys([chosen, ref]):
        fc[m] = E[m](seed=0).fit(actx, np.arange(len(data))).predict(actx, fut_idx)
    fc = fc.sort_values(chosen, ascending=False)
    fc.round(4).to_csv(OUT_DIR / "tahmin_2026.csv", index=False)

    # ---- figures
    G.feature_set_comparison([(s, best[s], summary.loc[best[s], "auc_mean"], *ci[best[s]])
                              for s in reversed(SET_ORDER)], OUT_DIR / "ozellik_seti.png")
    G.roc_pr(y, {best[s]: np.nanmean(oof[best[s]], axis=0) for s in SET_ORDER}, OUT_DIR / "roc_pr.png")

    row = cmp.set_index("model")
    gains = {s: (row.loc[best[s], "auc_diff_folds"], row.loc[best[s], "p_holm"])
             for s in SET_ORDER if best[s] != ref}
    supported = any(d > 0 and p < 0.05 for s, (d, p) in gains.items() if "Çaylak" in s)
    verdict = "DESTEKLENDİ" if supported else "DESTEKLENMEDİ"

    md = lambda d, **k: d.to_markdown(**k)
    L = ["# B1: Çaylak sezonundan sonraki sezonu tahmin\n",
         "Bu dosya `ders_projesi/gorev_b1.py` tarafından otomatik üretilir. Tasarım: `TASARIM.md`.\n",
         "## Hedef\n",
         f"- Sonraki normal sezonda `player_play` snap sayısı, kendi draft sınıfı ve pozisyon grubu "
         f"içinde ilk %{int(TOP_SHARE * 100)}'te (ve > 0).",
         f"- {len(data)} oyuncu (2023 sınıfı: çaylak 2023 → 2024; 2024 sınıfı: çaylak 2024 → 2025); "
         f"{y.sum()} pozitif (%{100 * y.mean():.1f}).",
         f"- Çaylak sezonunda normal sezon kaydı olmayan oyuncu: "
         f"{int((data['rk_snaps'] == 0).sum())}.\n",
         "## Sonuçlar (5-katlı × 5 tekrar)\n", md(summary.round(3)) + "\n",
         "![Özellik seti](ozellik_seti.png)\n", "![ROC ve PR](roc_pr.png)\n",
         f"**Friedman testi:** χ² = {fr[0]:.1f}, p = {fr[1]:.2e}\n",
         f"## Hipotez H-B1\n",
         f"Referans: **{ref}**. Çaylak sezonu bilgisinin AUC'yi anlamlı biçimde artıracağı "
         f"öngörülmüştü (Holm p < 0.05). Sonuç: **{verdict}**.\n",
         md(cmp.drop(columns="reference").round(4), index=False) + "\n",
         "## Zaman testi: 2023 sınıfıyla eğit, 2024 sınıfında test et\n",
         md(time_test.round(3), index=False) + "\n",
         "## Gelecek tahmini: 2025 sınıfı, 2026 sezonu\n",
         f"Seçilen model: **{chosen}**. Sonuç 2026 sezonu bitince belli olacak. "
         "Tam liste: `tahmin_2026.csv`. En yüksek 15:\n",
         md(fc.head(15).round(3), index=False) + "\n",
         "## Sınırlar\n",
         "- `player_play` hücum snaplerinin kariyer toplamının yaklaşık %79'unu kapsar; hedef buna göre okunmalıdır.",
         "- Hedef göreli bir tanımdır (sınıf ve pozisyon içinde ilk %25); \"starter\" ile aynı değildir.",
         "- Eğitim verisi iki draft sınıfıdır."]
    (OUT_DIR / "RAPOR.md").write_text("\n".join(L), encoding="utf-8")
    json.dump(dict(n=int(len(data)), pos=int(y.sum()), reference=ref, chosen=chosen,
                   verdict=verdict, seconds=round(time.time() - t0)),
              open(OUT_DIR / "calisma.json", "w"), indent=2, ensure_ascii=False)
    print(summary[["auc_mean", "auc_std", "auc_ci_low", "auc_ci_high", "ap_mean"]].round(3).to_string())
    print(time_test[["model", "auc", "ap"]].round(3).to_string(index=False))
    print(f"H-B1: {verdict}\nBitti: {OUT_DIR}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
