"""Forward prediction: will a player be an established starter over his first 3 seasons?

Only the 2023 draft class has all 3 seasons observed (2023-2025), so models are trained
and validated on it and then applied to the 2024 and 2025 classes, whose 3-season outcome
is not yet known (it ends after the 2026 and 2027 seasons). Inputs are pre-draft only.

Rules fixed before looking at results:
- target: career_games_started / 51 >= 0.5 (2023 class)
- validation: stratified 5-fold CV x 10 repeats inside the 2023 class
- the model with the highest mean CV AUC is the "chosen" model; draft-only is the reference
- supplementary time check: train on 2023, test on 2024 with its 2-season label (a proxy)

Run from the repo root:
    .venv-ml/bin/python -m ders_projesi.ileri_tahmin
"""
import json
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from . import grafikler as G
from .degerlendirme import (bootstrap_ci, compare_to_reference, cv_splits, metrics, run_cv,
                            summarize)
from .modeller import SkModel
from .ozellikler import _attempt_frames, add_dummies, tabular_feature_sets, tracking_summary
from .veri import OUT, load_players

warnings.filterwarnings("ignore", category=RuntimeWarning)  # macOS Accelerate matmul noise

TRAIN_CLASS = 2023
FUTURE_CLASSES = (2024, 2025)
HORIZON_GAMES = 51          # 3 seasons x 17 games
THRESHOLD = 0.5
OUT_DIR = OUT / "ileri_tahmin"
SET_LABEL = {"draft": "Draft", "combine": "Combine", "combine_trk": "Combine+Takip",
             "combine_trk_draft": "Combine+Takip+Draft"}
ALGOS = {"draft": ["LogReg", "GradBoost"],
         "combine": ["LogReg", "SVM", "RandomForest", "GradBoost"],
         "combine_trk": ["LogReg", "SVM", "RandomForest", "GradBoost"],
         "combine_trk_draft": ["LogReg", "SVM", "RandomForest", "GradBoost"]}


def feature_sets(df):
    # Draft-class dummies are constant inside a single training class, so drop them.
    return {k: [c for c in cols if not c.startswith("cohort_")]
            for k, cols in tabular_feature_sets(df).items()}


def experiments(sets):
    E = {}
    for key, algos in ALGOS.items():
        for a in algos:
            E[f"{SET_LABEL[key]} | {a}"] = (lambda a, key: lambda seed: SkModel(a, sets[key], seed))(a, key)
    return E


def main():
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_players()
    df = add_dummies(df.merge(tracking_summary(_attempt_frames()), on="nfl_id", how="left"))
    df["y_3yil"] = (df["career_games_started"] / HORIZON_GAMES >= THRESHOLD).astype(int)
    sets = feature_sets(df)
    E = experiments(sets)

    train = df[df["draft_year"] == TRAIN_CLASS].reset_index(drop=True)
    y = train["y_3yil"].to_numpy()
    ctx = dict(X=train, y=y)
    print(f"Eğitim: {TRAIN_CLASS} sınıfı {len(train)} oyuncu, {y.sum()} pozitif", flush=True)

    # ---- 1. validation inside the 2023 class
    splits = cv_splits(y, n_splits=5, n_repeats=10, seed=42)
    fold_df, oof = run_cv(E, ctx, splits)
    summary = summarize(fold_df)
    ci = {m: bootstrap_ci(y, np.nanmean(oof[m], axis=0)) for m in oof}
    summary.insert(0, "auc_ci_low", [ci[m][0] for m in summary.index])
    summary.insert(1, "auc_ci_high", [ci[m][1] for m in summary.index])
    chosen = summary.index[0]
    ref = max([m for m in summary.index if m.startswith("Draft |")],
              key=lambda m: summary.loc[m, "auc_mean"])
    cmp = compare_to_reference(fold_df, oof, y, ref)
    fold_df.to_csv(OUT_DIR / "katman_metrikleri.csv", index=False)
    summary.round(4).to_csv(OUT_DIR / "ozet.csv")
    cmp.round(4).to_csv(OUT_DIR / "test_draft_referans.csv", index=False)

    # Best model per feature set, used for the forward predictions.
    best = {}
    for s in SET_LABEL.values():
        ms = [m for m in summary.index if m.startswith(s + " |")]
        best[s] = max(ms, key=lambda m: summary.loc[m, "auc_mean"])
    shown = list(dict.fromkeys([chosen, ref] + list(best.values())))

    # ---- 2. supplementary time check: train 2023 -> test 2024 (2-season proxy label)
    proxy = df[df["draft_year"] == 2024].reset_index(drop=True)
    proxy_y = (proxy["career_games_started"] / 34 >= THRESHOLD).astype(int).to_numpy()
    full = pd.concat([train, proxy], ignore_index=True)
    fctx = dict(X=full, y=np.concatenate([y, proxy_y]))
    tr_idx, te_idx = np.arange(len(train)), np.arange(len(train), len(full))
    time_rows = []
    for m in shown:
        p = E[m](seed=0).fit(fctx, tr_idx).predict(fctx, te_idx)
        time_rows.append(dict(model=m, **metrics(proxy_y, p)))
    time_check = pd.DataFrame(time_rows)
    time_check.round(4).to_csv(OUT_DIR / "zaman_kontrolu_2024.csv", index=False)

    # ---- 3. forward predictions for 2024 and 2025 classes (fit on all of 2023)
    future = df[df["draft_year"].isin(FUTURE_CLASSES)].reset_index(drop=True)
    allx = pd.concat([train, future], ignore_index=True)
    actx = dict(X=allx, y=np.concatenate([y, np.zeros(len(future), int)]))
    fut_idx = np.arange(len(train), len(allx))
    pred = future[["nfl_id", "display_name", "draft_year", "nfl_position", "position_group",
                   "draft_overall_pick", "seasons_available", "career_games_started",
                   "start_rate"]].copy()
    pred = pred.rename(columns={"seasons_available": "gozlenen_sezon",
                                "career_games_started": "simdiye_kadar_ilk11",
                                "start_rate": "simdiye_kadar_oran"})
    pred["sonucun_belli_olacagi_sezon"] = pred["draft_year"] + 2
    for m in shown:
        model = E[m](seed=0).fit(actx, np.arange(len(train)))
        pred[m] = model.predict(actx, fut_idx)
    pred = pred.sort_values(chosen, ascending=False)
    pred.round(4).to_csv(OUT_DIR / "gelecek_tahminleri.csv", index=False)

    # Partial consistency (NOT validation): does the forecast agree with seasons seen so far?
    sofar = (pred["simdiye_kadar_oran"] >= THRESHOLD).astype(int)
    partial = pd.DataFrame([dict(model=m, draft_year=c,
                                 auc_simdiye_kadar=roc_auc_score(sofar[pred.draft_year == c],
                                                                 pred.loc[pred.draft_year == c, m]))
                            for m in shown for c in FUTURE_CLASSES])
    partial.round(4).to_csv(OUT_DIR / "kismi_tutarlilik.csv", index=False)

    # ---- figures
    G.feature_set_comparison(
        [(s, best[s], summary.loc[best[s], "auc_mean"], *ci[best[s]])
         for s in reversed(list(SET_LABEL.values()))], OUT_DIR / "ozellik_seti.png")
    G.calibration(y, {m: np.nanmean(oof[m], axis=0) for m in [chosen, ref]},
                  OUT_DIR / "kalibrasyon.png")

    write_report(train, y, summary, cmp, chosen, ref, time_check, pred, partial, best, len(splits))
    json.dump(dict(train_players=int(len(train)), train_pos=int(y.sum()),
                   future_players=int(len(pred)), chosen=chosen, reference=ref,
                   seconds=round(time.time() - t0)),
              open(OUT_DIR / "calisma.json", "w"), indent=2, ensure_ascii=False)
    print(summary[["auc_mean", "auc_std", "auc_ci_low", "auc_ci_high", "brier_mean"]].round(3).to_string())
    print(time_check.round(3).to_string(index=False))
    print(f"Bitti: {OUT_DIR}  ({time.time() - t0:.0f}s)")


def write_report(train, y, summary, cmp, chosen, ref, time_check, pred, partial, best, n_folds):
    md = lambda d, **k: d.to_markdown(**k)
    L = ["# Gelecek tahmini: ilk 3 sezonda kalıcı starter olacak mı?\n",
         "Bu dosya `ders_projesi/ileri_tahmin.py` tarafından otomatik üretilir.\n",
         "## Tasarım (sonuçlar görülmeden belirlendi)\n",
         f"- **Hedef:** ilk 3 sezonda (51 maç) en az %50 maçta ilk 11'de başlamak.",
         f"- **Eğitim/doğrulama:** yalnızca 3 sezonu tamamen gözlenen 2023 sınıfı: "
         f"{len(train)} oyuncu, {y.sum()} pozitif (%{100 * y.mean():.1f}).",
         f"- **Doğrulama:** tabakalı 5-katlı çapraz doğrulama × 10 tekrar ({n_folds} test).",
         "- **Model seçimi:** en yüksek ortalama AUC; referans en iyi draft-only model.",
         "- **Girdiler:** yalnızca draft öncesi bilgiler (draft, combine, combine takip özeti). "
         "Oyuncunun NFL'de oynadığı sezonlar girdi değildir.",
         "- CNN bu analize alınmadı: 160 oyunculuk eğitim verisi derin öğrenme için çok küçük.\n",
         "## 1. Doğrulama sonuçları (2023 sınıfı içinde)\n",
         md(summary.round(3)) + "\n",
         f"**Seçilen model:** {chosen}  ·  **Referans:** {ref}\n",
         "![Özellik seti](ozellik_seti.png)\n",
         "### Referansla karşılaştırma (düzeltilmiş t-testi + Holm, eşli bootstrap)\n",
         md(cmp.drop(columns="reference").round(4), index=False) + "\n",
         "![Kalibrasyon](kalibrasyon.png)\n",
         "## 2. Ek zaman kontrolü: 2023 ile eğit, 2024'te test et\n",
         "2024 sınıfının 3. sezonu henüz oynanmadığı için hedef olarak 2 sezonluk oran "
         "(34 maçta ≥ %50) kullanıldı. Bu, asıl hedefin **yaklaşık** bir karşılığıdır.\n",
         md(time_check.round(3), index=False) + "\n",
         "## 3. Gelecek tahminleri (2024 ve 2025 sınıfları)\n",
         f"{len(pred)} oyuncu. Sonuç 2024 sınıfı için 2026, 2025 sınıfı için 2027 sezonu "
         "sonunda belli olacak; bu tahminlerin doğruluğu bugün ölçülemez. Tam liste: "
         "`gelecek_tahminleri.csv`.\n",
         f"**Seçilen modele göre en yüksek olasılıklı 15 oyuncu:**\n",
         md(pred[["display_name", "draft_year", "nfl_position", "draft_overall_pick",
                  "simdiye_kadar_oran", chosen]].head(15).round(3), index=False) + "\n",
         "### Kısmi tutarlılık (doğrulama değildir)\n",
         "Tahminin, bu oyuncuların şimdiye kadar oynadığı sezonlardaki starter durumuyla ne "
         "kadar uyuştuğu (AUC). 2025 sınıfında yalnız 1 sezon gözlendi.\n",
         md(partial.round(3), index=False) + "\n",
         "## Sınırlar\n",
         f"- Eğitim verisi küçüktür ({len(train)} oyuncu, {y.sum()} pozitif); güven aralıkları geniştir.",
         "- Model tek bir draft sınıfından öğrenir; sınıflar arası farklar (ör. kadro ihtiyacı) modelde yoktur.",
         "- Gelecek tahminleri ancak 2026 ve 2027 sezonları bitince doğrulanabilir."]
    (OUT_DIR / "RAPOR.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
