"""Task A: can pre-draft data predict which players become established NFL starters?

Main target: start_rate >= 0.5. Sensitivity targets: thresholds 0.4 / 0.6 and a
position-adjusted label (top 20% snaps per season within position group and draft class).

Run from the repo root:
    .venv-ml/bin/python -m ders_projesi.gorev_a                       # full (5x5 CV)
    .venv-ml/bin/python -m ders_projesi.gorev_a --quick --cnn-epochs 2  # smoke run
"""
import argparse
import json
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score

from . import grafikler as G
from .degerlendirme import (bootstrap_ci, compare_to_reference, cv_splits, friedman,
                            run_cv, run_leave_cohort_out, summarize)
from .modeller import CNNModel, SkModel
from .ozellikler import (_attempt_frames, add_dummies, build_sequences, tabular_feature_sets,
                         tracking_summary)
from .veri import OUT, load_players

warnings.filterwarnings("ignore", category=RuntimeWarning)  # macOS Accelerate matmul noise

MAIN = "y_starter"
TARGETS = {
    "y_starter": "Starter ≥ 0.5 (ana)",
    "y_starter_40": "Starter ≥ 0.4",
    "y_starter_60": "Starter ≥ 0.6",
    "y_pos_top20": "Pozisyonunda ilk %20",
}
SET_KEYS = {"Draft": "draft", "Combine": "combine", "Combine+Takip": "combine_trk",
            "Combine+Takip+Draft": "combine_trk_draft"}
SET_ORDER = ["Draft", "Combine", "Combine+Takip", "Combine+Takip+Draft", "Takip dizisi"]
SK_ALGOS = ["LogReg", "kNN", "SVM", "RandomForest", "GradBoost", "MLP"]


def build_context():
    df = load_players()
    ct = _attempt_frames()
    df = add_dummies(df.merge(tracking_summary(ct), on="nfl_id", how="left"))
    seq = build_sequences(df["nfl_id"].to_numpy(), ct)
    return df, dict(X=df, y=df[MAIN].to_numpy(), seq=seq)


def experiments(sets, cnn_epochs=80, with_cnn=True):
    def sk(a, key):
        return lambda seed: SkModel(a, sets[key], seed)

    E = {"Draft | Dummy": sk("Dummy", "draft")}
    for a in ["LogReg", "GradBoost"]:
        E[f"Draft | {a}"] = sk(a, "draft")
    for label in ["Combine", "Combine+Takip", "Combine+Takip+Draft"]:
        for a in SK_ALGOS:
            E[f"{label} | {a}"] = sk(a, SET_KEYS[label])
    if with_cnn:
        E["Takip dizisi | CNN"] = lambda seed: CNNModel("CNN", None, seed, epochs=cnn_epochs)
        E["Combine+Takip | CNN-Hibrit"] = lambda seed: CNNModel(
            "CNN-Hibrit", sets["combine"], seed, epochs=cnn_epochs)
        E["Combine+Takip+Draft | CNN-Hibrit"] = lambda seed: CNNModel(
            "CNN-Hibrit", sets["combine"] + sets["draft"], seed, epochs=cnn_epochs)
    return E


def best_per_set(summary, only_sklearn=False):
    out = {}
    for s in SET_ORDER:
        ms = [m for m in summary.index if G.set_of(m) == s and "Dummy" not in m
              and not (only_sklearn and "CNN" in m)]
        if ms:
            out[s] = max(ms, key=lambda m: summary.loc[m, "auc_mean"])
    return out


def per_position_auc(df, y, preds):
    rows, counts = {}, {}
    for pg, sub in df[df["position_group"] != "OTHER"].groupby("position_group"):
        idx = sub.index.to_numpy()
        pos = int(y[idx].sum())
        counts[pg] = dict(n=len(idx), pos=pos)
        rows[pg] = {s: (roc_auc_score(y[idx], p[idx]) if 5 <= pos <= len(idx) - 5 else np.nan)
                    for s, p in preds.items()}
    return pd.DataFrame(rows).T, pd.DataFrame(counts).T


def honors_check(df, preds):
    hon = df["y_honors"].to_numpy() == 1
    rows = []
    for s, p in preds.items():
        pct = pd.Series(p).rank(pct=True).to_numpy()
        rows.append(dict(set=s, honors_n=int(hon.sum()),
                         honors_mean_percentile=pct[hon].mean(),
                         honors_min_percentile=pct[hon].min(),
                         auc_honors_vs_rest=roc_auc_score(hon.astype(int), p)))
    return pd.DataFrame(rows)


def perm_importance(ctx, model_name, make, splits, cols):
    """Permutation importance (AUC drop) averaged over the 5 folds of repeat 0."""
    y, X, acc = ctx["y"], ctx["X"], []
    for rep, fold, tr, te in splits:
        if rep != 0:
            continue
        m = make(seed=fold).fit(ctx, tr)
        r = permutation_importance(m.pipe, X.iloc[te][cols], y[te], scoring="roc_auc",
                                   n_repeats=10, random_state=fold)
        acc.append(pd.Series(r.importances_mean, index=cols))
    return pd.concat(acc, axis=1).mean(axis=1).sort_values(ascending=False)


def md(df, **kw):
    return df.to_markdown(**kw)


def write_report(out, df, res, extra):
    s = res[MAIN]
    summary, ci = s["summary"], s["ci"]
    L = ["# Görev A: Draft öncesi veriden kalıcı starter tahmini\n",
         "Bu dosya `ders_projesi/gorev_a.py` tarafından otomatik üretilir; "
         "tablolardaki her sayı aynı çalıştırmanın çıktısıdır.\n",
         "## 1. Hedef tanımları\n",
         "- `start_rate = career_games_started / (17 × oynanabilir sezon)`; kariyer verisi 2025 "
         "sezonu sonuna kadardır (2023 sınıfı 3, 2024 sınıfı 2, 2025 sınıfı 1 sezon).",
         "- **Ana hedef:** `start_rate ≥ 0.5` (kalıcı starter). Bu tanım \"yıldız\" değil, "
         "\"takımında kalıcı yer edinen oyuncu\" anlamına gelir.",
         "- **Dayanıklılık hedefleri:** eşik 0.4 ve 0.6; pozisyona göre ayarlı tanım = aynı pozisyon "
         "grubu ve draft sınıfı içinde sezon başına snap (hücum + savunma) sıralamasında ilk %20. "
         "OTHER grubu (1 RB, 1 FB) kendi içinde sıralanamadığı için bu tanımda pozitif sayılmaz.\n"]
    cnt = pd.DataFrame({TARGETS[t]: [int(df[t].sum()), round(100 * df[t].mean(), 1)]
                        for t in TARGETS}, index=["pozitif", "%"]).T
    L += [md(cnt) + "\n",
          "![Hedef dağılımı](hedef_dagilimi.png)\n",
          "![Pozisyona göre starter oranı](pozisyon_oran.png)\n",
          "![Draft sırası ve sonuç](draft_vs_sonuc.png)\n",
          "## 2. Protokol\n",
          f"- Tekrarlı tabakalı 5-katlı çapraz doğrulama × {extra['n_rep']} tekrar "
          "(tabaka = etiket × draft yılı); tüm modeller aynı bölmeleri kullanır.",
          "- Ön işleme (medyan doldurma + eksik göstergesi + standartlaştırma) yalnız eğitim katmanında öğrenilir.",
          "- Model ayarları sabittir (ayar araması yapılmadı); bu, modeller arası adil karşılaştırma "
          "içindir, her modelin en iyi hâlini temsil etmez.",
          "- CNN: her dril denemesi (hız, ivme, dönüş hızı, kümülatif mesafe; 10 Hz) 1D-CNN ile "
          "kodlanır, oyuncunun tüm denemeleri ortalanır. Hibrit model bu gömmeyi tablo "
          "özellikleriyle birleştirir. CNN modelleri yalnız ana hedefte çalıştırıldı.\n",
          "## 3. Ana sonuçlar\n",
          "![Özellik seti karşılaştırması](ozellik_seti.png)\n"]
    t = summary.copy()
    t.insert(0, "AUC %95 GA (OOF)", [f"[{ci[m][0]:.3f}, {ci[m][1]:.3f}]" for m in t.index])
    L += [md(t.round(3)) + "\n", "![Tüm modeller](auc_kutu.png)\n",
          "![ROC ve PR](roc_pr.png)\n", "![Kalibrasyon](kalibrasyon.png)\n"]
    fr = s["friedman"]
    L += ["## 4. İstatistiksel testler\n",
          f"**Friedman testi** (Dummy hariç tüm modeller, katman AUC'leri): χ² = {fr[0]:.1f}, "
          f"p = {fr[1]:.2e}\n", "Ortalama sıra (1 = en iyi), ilk 10:\n",
          md(fr[2].head(10).round(2).to_frame("ortalama_sıra")) + "\n",
          f"**Referans = en iyi Draft modeli ({s['ref_draft']})**. Düzeltilmiş t-testi: "
          "Nadeau & Bengio (2003), Holm düzeltmeli. Bootstrap: OOF tahminlerinde eşli 2000 tekrar.\n",
          md(s["cmp_draft"].drop(columns="reference").round(4), index=False) + "\n",
          "## 5. Draft sınıfı dışarıda bırakma\n",
          "İki draft sınıfıyla eğit, üçüncüsünde test et (ana hedef).\n",
          md(s["loco"].pivot_table(index="model", columns="test_cohort", values="auc").round(3)) + "\n",
          "## 6. Dayanıklılık: hedef tanımı değişince\n",
          "Her hücre o özellik setinin o hedefte en iyi sklearn modelinin 5×5 CV ortalama AUC'sidir.\n",
          md(extra["sens"].round(3)) + "\n", "![Dayanıklılık](dayaniklilik.png)\n",
          "## 7. Pozisyon grubuna göre (ana hedef, OOF tahminleri)\n",
          "5'ten az pozitif veya negatif örneği olan hücreler boş bırakıldı.\n",
          md(extra["pos_auc"].round(3)) + "\n", md(extra["pos_cnt"]) + "\n",
          "![Pozisyon AUC](pozisyon_auc.png)\n",
          "## 8. Ödüllü oyuncu kontrolü (All-Pro / Pro Bowl)\n",
          "Ödüllü oyuncular model hedefi değildir; modelin onları üst sıralara koyup koymadığına bakılır. "
          "Yüzdelik = oyuncunun 510 kişi içindeki tahmin sırası (1.0 = en yüksek).\n",
          md(extra["honors"].round(3), index=False) + "\n",
          "## 9. Hangi bilgi önemli? (permütasyon önemi, ilk 12)\n"]
    for name, imp in extra["imp"].items():
        L += [f"**{name}**\n", md(imp.head(12).round(4).to_frame("AUC_kaybı")) + "\n"]
    L += ["![Önem combine](onem_combine.png)\n", "![Önem draft dahil](onem_draft.png)\n",
          "## 10. Sınırlar\n",
          "- Örnek küçüktür (510 oyuncu, ana hedefte 103 pozitif); güven aralıkları buna göre okunmalıdır.",
          "- 2025 sınıfı için hedef yalnız çaylak sezonunu yansıtır.",
          "- Kariyer toplamları sezonlara bölünmüş değildir; bu görevde yalnız hedef olarak kullanıldı.",
          "- Model ayarları aranmadı; daha iyi ayarlarla mutlak skorlar değişebilir."]
    (out / "RAPOR.md").write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--cnn-epochs", type=int, default=80)
    args = ap.parse_args()
    n_rep = 1 if args.quick else args.repeats
    out = OUT / ("gorev_a_quick" if args.quick else "gorev_a")
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    df, ctx = build_context()
    sets = tabular_feature_sets(df)
    cohort = df["draft_year"].to_numpy()
    res = {}
    for target, label in TARGETS.items():
        y = df[target].to_numpy()
        ctx["y"] = y
        splits = cv_splits(y * 10000 + cohort, n_splits=5, n_repeats=n_rep)
        E = experiments(sets, args.cnn_epochs, with_cnn=(target == MAIN))
        print(f"\n== {label}: {y.sum()} pozitif; {len(E)} model × {len(splits)} katman", flush=True)
        fold_df, oof = run_cv(E, ctx, splits)
        summary = summarize(fold_df)
        sub = out / target
        sub.mkdir(exist_ok=True)
        fold_df.to_csv(sub / "katman_metrikleri.csv", index=False)
        summary.round(4).to_csv(sub / "ozet.csv")
        pred = pd.DataFrame({m: np.nanmean(p, axis=0) for m, p in oof.items()})
        pred.insert(0, "nfl_id", df["nfl_id"])
        pred.insert(1, target, y)
        pred.to_csv(sub / "oof_tahminler.csv", index=False)
        res[target] = dict(summary=summary, fold_df=fold_df, oof=oof, splits=splits, E=E)

    # ---- detailed analyses on the main target
    y = df[MAIN].to_numpy()
    ctx["y"] = y
    s = res[MAIN]
    summary, oof, E = s["summary"], s["oof"], s["E"]
    s["ci"] = {m: bootstrap_ci(y, np.nanmean(oof[m], axis=0)) for m in oof}
    best = best_per_set(summary)
    s["ref_draft"] = best["Draft"]
    s["cmp_draft"] = compare_to_reference(s["fold_df"], oof, y, best["Draft"])
    s["cmp_draft"].to_csv(out / MAIN / "test_draft_referans.csv", index=False)
    s["friedman"] = friedman(s["fold_df"], [m for m in summary.index if "Dummy" not in m])
    s["loco"] = run_leave_cohort_out({m: E[m] for m in best.values()}, ctx, cohort)
    s["loco"].to_csv(out / MAIN / "sinif_disarida.csv", index=False)
    best_preds = {k: np.nanmean(oof[m], axis=0) for k, m in best.items()}
    pos_auc, pos_cnt = per_position_auc(df, y, best_preds)
    honors = honors_check(df, best_preds)
    honors.insert(1, "model", [best[k] for k in honors["set"]])
    sens = pd.DataFrame({TARGETS[t]: {k: res[t]["summary"].loc[m, "auc_mean"]
                                      for k, m in best_per_set(res[t]["summary"], True).items()}
                         for t in TARGETS})
    sk_best = best_per_set(summary, only_sklearn=True)
    imp = {}
    for k, fig_name in [("Combine+Takip", "onem_combine.png"), ("Combine+Takip+Draft", "onem_draft.png")]:
        m = sk_best[k]
        imp[m] = perm_importance(ctx, m, E[m], s["splits"], sets[SET_KEYS[k]])
        G.importance(imp[m].head(12), out / fig_name, f"{m}: en önemli 12 özellik")
    pd.concat(imp, axis=1).to_csv(out / MAIN / "permutasyon_onemi.csv")

    # ---- figures
    G.target_distribution(df, out / "hedef_dagilimi.png")
    G.positive_rate_by_position(df, MAIN, out / "pozisyon_oran.png",
                                "Pozisyon grubuna göre starter oranı (OTHER hariç)")
    G.draft_vs_outcome(df, out / "draft_vs_sonuc.png")
    G.feature_set_comparison(
        [(k, best[k], summary.loc[best[k], "auc_mean"], *s["ci"][best[k]])
         for k in reversed(SET_ORDER) if k in best], out / "ozellik_seti.png")
    G.auc_box(s["fold_df"][~s["fold_df"].model.str.contains("Dummy")], out / "auc_kutu.png")
    G.roc_pr(y, {best[k]: best_preds[k] for k in best}, out / "roc_pr.png")
    G.calibration(y, {best[k]: best_preds[k] for k in best if k != "Takip dizisi"},
                  out / "kalibrasyon.png")
    G.sensitivity(sens, out / "dayaniklilik.png")
    G.position_heatmap(pos_auc, pos_cnt, out / "pozisyon_auc.png")

    write_report(out, df, res, dict(n_rep=n_rep, sens=sens, pos_auc=pos_auc, pos_cnt=pos_cnt,
                                    honors=honors, imp=imp))
    json.dump(dict(n_players=int(len(df)), targets={t: int(df[t].sum()) for t in TARGETS},
                   n_folds=len(s["splits"]), seconds=round(time.time() - t0)),
              open(out / "calisma.json", "w"), indent=2)
    print(summary[["auc_mean", "auc_std", "ap_mean", "brier_mean"]].round(3).to_string())
    print(f"Bitti: {out}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
