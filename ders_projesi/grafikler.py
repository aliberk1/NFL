"""Report figures (static PNG). One question per figure; colour = feature set, fixed order."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import precision_recall_curve, roc_auc_score, roc_curve

# Validated categorical palette (light mode), assigned in fixed order to feature sets.
SET_COLORS = {
    "Draft": "#257de0",
    "Combine": "#f47230",
    "Combine+Takip": "#00b894",
    "Combine+Takip+Draft": "#f2a600",
    "Takip dizisi": "#ee7fac",
}
NEUTRAL = "#9c9c9c"
TEXT = "#191919"
TEXT2 = "#666666"
GRID = "#e6e6e6"

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": TEXT, "text.color": TEXT,
    "xtick.color": TEXT2, "ytick.color": TEXT2, "axes.grid": True, "grid.color": GRID,
    "grid.linestyle": "-", "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold",
    "axes.titlesize": 10, "legend.frameon": False, "savefig.dpi": 160,
})


def set_of(model_name):
    return model_name.split(" | ")[0]


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def target_distribution(df, path):
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.hist(df["start_rate"], bins=np.linspace(0, 1, 21), color=SET_COLORS["Draft"],
            edgecolor="white", linewidth=1.5)
    for t, lab in [(0.4, "0.4"), (0.5, "0.5 (ana eşik)"), (0.6, "0.6")]:
        ax.axvline(t, color=TEXT if t == 0.5 else TEXT2, lw=1.2 if t == 0.5 else 0.8)
        ax.text(t + 0.01, ax.get_ylim()[1] * 0.92, lab, fontsize=8, color=TEXT2)
    ax.set_xlabel("İlk 11 başlama oranı = başladığı maç / (17 × oynanabilir sezon)")
    ax.set_ylabel("Oyuncu sayısı")
    ax.set_title("Oyuncuların ilk 11 başlama oranı dağılımı (n = %d)" % len(df))
    _save(fig, path)


def positive_rate_by_position(df, col, path, title):
    g = df[df["position_group"] != "OTHER"].groupby("position_group")[col].agg(["mean", "sum", "size"])
    g = g.sort_values("mean")
    fig, ax = plt.subplots(figsize=(6.0, 2.8))
    ax.barh(g.index, g["mean"] * 100, color=SET_COLORS["Draft"], height=0.6)
    for i, (m, s, n) in enumerate(g.itertuples(index=False)):
        ax.text(m * 100 + 0.8, i, f"%{m * 100:.0f}  ({s}/{n})", va="center", fontsize=8, color=TEXT)
    ax.set_xlabel("Pozitif sınıf oranı (%)")
    ax.set_xlim(0, max(g["mean"]) * 100 * 1.35)
    ax.set_title(title)
    ax.grid(axis="y", visible=False)
    _save(fig, path)


def draft_vs_outcome(df, path):
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    rng = np.random.default_rng(0)
    x = df["pick_filled"] + np.where(df["undrafted"] == 1, rng.uniform(-4, 4, len(df)), 0)
    hon = df["y_honors"] == 1
    ax.scatter(x[~hon], df.loc[~hon, "start_rate"], s=12, color=NEUTRAL, alpha=0.6,
               linewidths=0, label="Diğer oyuncular")
    ax.scatter(x[hon], df.loc[hon, "start_rate"], s=36, color=SET_COLORS["Draft"],
               edgecolors="white", linewidths=1.5, label="All-Pro / Pro Bowl (n = %d)" % hon.sum())
    ax.axhline(0.5, color=TEXT2, lw=0.8)
    ax.text(2, 0.52, "starter eşiği", fontsize=8, color=TEXT2)
    ax.set_xlabel("Draft sırası (262 = draft edilmedi)")
    ax.set_ylabel("İlk 11 başlama oranı")
    ax.set_title("Draft sırası ve kariyer sonucu")
    ax.legend(loc="upper right", fontsize=8)
    _save(fig, path)


def feature_set_comparison(rows, path, xlabel="ROC-AUC (OOF, %95 bootstrap güven aralığı)",
                           xlim=(0.45, 1.0), chance=0.5, chance_label="şans düzeyi"):
    """rows: list of (set_label, model_name, score, lo, hi), drawn bottom->top in given order."""
    fig, ax = plt.subplots(figsize=(6.4, 0.55 * len(rows) + 1.0))
    for i, (s, m, auc, lo, hi) in enumerate(rows):
        c = SET_COLORS[s]
        ax.plot([lo, hi], [i, i], color=c, lw=2, solid_capstyle="round")
        ax.scatter([auc], [i], s=60, color=c, edgecolors="white", linewidths=2, zorder=3)
        ax.text(hi + 0.008, i, f"{auc:.3f}", va="center", fontsize=8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"{s}\n({m.split(' | ')[1]})" for s, m, *_ in rows], fontsize=8)
    ax.axvline(chance, color=TEXT2, lw=0.8)
    ax.text(chance + 0.003, len(rows) - 0.55, chance_label, fontsize=7, color=TEXT2)
    ax.set_xlim(*xlim)
    ax.set_xlabel(xlabel)
    ax.set_title("Her özellik setinin en iyi modeli")
    ax.grid(axis="y", visible=False)
    _save(fig, path)


def auc_box(fold_df, path):
    order = fold_df.groupby("model")["auc"].mean().sort_values().index
    fig, ax = plt.subplots(figsize=(7.0, 0.3 * len(order) + 1.2))
    data = [fold_df.loc[fold_df.model == m, "auc"].to_numpy() for m in order]
    bp = ax.boxplot(data, vert=False, widths=0.55, patch_artist=True, showfliers=False,
                    medianprops=dict(color=TEXT, lw=1.2), whiskerprops=dict(color=TEXT2),
                    capprops=dict(color=TEXT2))
    for patch, m in zip(bp["boxes"], order):
        patch.set_facecolor(SET_COLORS[set_of(m)])
        patch.set_edgecolor("white")
    ax.set_yticks(range(1, len(order) + 1))
    ax.set_yticklabels(order, fontsize=7.5)
    ax.axvline(0.5, color=TEXT2, lw=0.8)
    ax.set_xlabel(f"ROC-AUC (her kutu = {len(data[0])} test katmanı)")
    ax.set_title("Tüm modeller: katman bazında AUC")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in SET_COLORS.values()]
    ax.legend(handles, SET_COLORS.keys(), loc="lower right", fontsize=7)
    ax.grid(axis="y", visible=False)
    _save(fig, path)


def roc_pr(y, preds, path):
    """preds: {model_name: oof_prob}; up to 5 series coloured by feature set."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.0, 4.0))
    for m, p in preds.items():
        c = SET_COLORS[set_of(m)]
        fpr, tpr, _ = roc_curve(y, p)
        a1.plot(fpr, tpr, color=c, lw=2, label=f"{m} ({roc_auc_score(y, p):.3f})")
        pr, rc, _ = precision_recall_curve(y, p)
        a2.plot(rc, pr, color=c, lw=2, label=m)
    a1.plot([0, 1], [0, 1], color=NEUTRAL, lw=0.8)
    a2.axhline(y.mean(), color=NEUTRAL, lw=0.8)
    a2.text(0.62, y.mean() + 0.02, f"şans düzeyi = {y.mean():.2f}", fontsize=7, color=TEXT2)
    a1.set(xlabel="Yanlış pozitif oranı", ylabel="Doğru pozitif oranı", title="ROC eğrisi")
    a2.set(xlabel="Duyarlılık (recall)", ylabel="Kesinlik (precision)", title="Precision-Recall eğrisi")
    a1.legend(fontsize=7, loc="lower right")
    _save(fig, path)


def calibration(y, preds, path):
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    ax.plot([0, 1], [0, 1], color=NEUTRAL, lw=0.8, label="Kusursuz kalibrasyon")
    for m, p in preds.items():
        frac, mean = calibration_curve(y, p, n_bins=8, strategy="quantile")
        ax.plot(mean, frac, color=SET_COLORS[set_of(m)], lw=2, marker="o", ms=5,
                markeredgecolor="white", label=m)
    ax.set(xlabel="Tahmin edilen olasılık", ylabel="Gerçekleşen oran",
           title="Kalibrasyon: tahmin edilen olasılık doğru mu?")
    ax.legend(fontsize=7, loc="upper left")
    _save(fig, path)


def sensitivity(table, path):
    """table: DataFrame index=feature set label, columns=target labels, values=AUC."""
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    x = np.arange(len(table.columns))
    for s, row in table.iterrows():
        c = SET_COLORS[s]
        ax.plot(x, row.values, color=c, lw=2, marker="o", ms=7, markeredgecolor="white")
        ax.text(x[-1] + 0.08, row.values[-1], s, va="center", fontsize=8, color=TEXT)
    ax.set_xticks(x)
    ax.set_xticklabels(table.columns, fontsize=8)
    ax.set_xlim(-0.3, len(x) - 1 + 1.3)
    ax.set_ylabel("ROC-AUC (en iyi model, 5×5 CV)")
    ax.set_title("Hedef tanımı değişince sonuç değişiyor mu?")
    _save(fig, path)


def position_heatmap(table, counts, path):
    """table: index=position group, columns=feature set label, values=AUC."""
    fig, ax = plt.subplots(figsize=(6.6, 0.5 * len(table) + 1.4))
    im = ax.imshow(table.values, cmap="Blues", vmin=0.3, vmax=1.0, aspect="auto")
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            v = table.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if v > 0.75 else TEXT)
    ax.set_xticks(range(table.shape[1]))
    ax.set_xticklabels([c.replace("+", "+\n") for c in table.columns], fontsize=8)
    ax.set_yticks(range(table.shape[0]))
    ax.set_yticklabels([f"{p}  (n={counts.loc[p, 'n']}, +{counts.loc[p, 'pos']})"
                        for p in table.index], fontsize=8)
    ax.grid(False)
    fig.colorbar(im, ax=ax, label="ROC-AUC", shrink=0.8)
    ax.set_title("Pozisyon grubuna göre AUC (en iyi model / set)")
    _save(fig, path)


def importance(imp, path, title):
    """imp: Series feature -> mean AUC drop, sorted descending, already truncated."""
    imp = imp.iloc[::-1]
    fig, ax = plt.subplots(figsize=(6.0, 0.32 * len(imp) + 1.0))
    ax.barh(imp.index, imp.values, color=SET_COLORS["Combine"], height=0.6)
    ax.axvline(0, color=TEXT2, lw=0.8)
    ax.set_xlabel("Permütasyon önemi: karıştırılınca AUC kaybı")
    ax.set_title(title)
    ax.grid(axis="y", visible=False)
    _save(fig, path)


def pred_vs_actual(y, p, path, title, xlabel, ylabel):
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    ax.scatter(p, y, s=12, color=SET_COLORS["Draft"], alpha=0.55, linewidths=0)
    lim = [min(np.min(y), np.min(p)), max(np.max(y), np.max(p))]
    ax.plot(lim, lim, color=NEUTRAL, lw=0.8)
    ax.text(lim[1], lim[1], " kusursuz tahmin", fontsize=7, color=TEXT2, va="bottom", ha="right")
    ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
    _save(fig, path)
