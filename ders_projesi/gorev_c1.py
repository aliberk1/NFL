"""C1: recognise the route a player ran from his game tracking (play level). Design: TASARIM.md.

Input: 35 frames (3.5 s at 10 Hz) from the ball_snap frame. Coordinates are rotated so the
offense moves toward +x, shifted to start at (0, 0), and mirrored so +y points toward the field
centre (an approximation of "inside": tracking has no ball position).

Run from the repo root:
    .venv-ml/bin/python -m ders_projesi.gorev_c1
"""
import json
import time
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from scipy import stats
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torch import nn

from . import grafikler as G
from .degerlendirme import corrected_ttest, holm
from .modeller import DEVICE
from .veri import OUT, read

warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

OUT_DIR = OUT / "gorev_c1"
CACHE = OUT / "cache" / "route_sequences.npz"
T = 35
MIN_FRAMES = 15
MIN_CLASS = 300
FIELD_MID_Y = 53.3 / 2
CHANNELS = ["dx", "dy", "vx", "vy", "s", "a"]


# ----------------------------------------------------------------- data ----

def build_sequences():
    if CACHE.exists():
        z = np.load(CACHE, allow_pickle=True)
        return {k: z[k] for k in z.files}
    pp = read("player_play.csv", usecols=["game_id", "play_id", "nfl_id", "route_ran",
                                          "play_direction"], low_memory=False)
    pp = pp[pp["route_ran"].notna()]
    games = read("games.csv")[["game_id", "season"]]
    pp = pp.merge(games, on="game_id")
    seqs, masks, meta = [], [], []
    for season in (2023, 2024, 2025):
        lab = pp[pp["season"] == season]
        t = read(f"game_tracking_{season}.csv",
                 usecols=["game_id", "play_id", "nfl_id", "time", "x", "y", "s", "a", "event"])
        t = t.merge(lab[["game_id", "play_id", "nfl_id"]], on=["game_id", "play_id", "nfl_id"])
        t = t.sort_values(["game_id", "play_id", "nfl_id", "time"])
        lab = lab.set_index(["game_id", "play_id", "nfl_id"])
        for key, g in t.groupby(["game_id", "play_id", "nfl_id"], sort=False):
            snap = np.flatnonzero(g["event"].to_numpy() == "ball_snap")
            if len(snap) == 0:
                continue
            w = g.iloc[snap[0]:snap[0] + T]
            if len(w) < MIN_FRAMES:
                continue
            x, y = w["x"].to_numpy(float), w["y"].to_numpy(float)
            if lab.at[key, "play_direction"] == "left":
                x, y = 120 - x, 53.3 - y
            dx, dy = x - x[0], y - y[0]
            if y[0] > FIELD_MID_Y:
                dy = -dy
            vx = np.diff(dx, prepend=dx[0]) * 10
            vy = np.diff(dy, prepend=dy[0]) * 10
            arr = np.stack([dx, dy, vx, vy, w["s"].to_numpy(float), w["a"].to_numpy(float)], 1)
            pad = np.zeros((T, len(CHANNELS)), np.float32)
            m = np.zeros(T, np.float32)
            pad[:len(arr)], m[:len(arr)] = arr, 1
            pad[len(arr):] = arr[-1] * np.array([1, 1, 0, 0, 0, 0])  # hold final position
            seqs.append(pad)
            masks.append(m)
            meta.append((key[0], key[1], key[2], season, lab.at[key, "route_ran"]))
        del t
    meta = np.array(meta, dtype=object)
    out = dict(seq=np.stack(seqs).astype(np.float32), mask=np.stack(masks),
               game_id=meta[:, 0].astype(np.int64), play_id=meta[:, 1].astype(np.int64),
               nfl_id=meta[:, 2].astype(np.int64), season=meta[:, 3].astype(np.int64),
               route=meta[:, 4].astype(str))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE, **out)
    return out


def handcrafted(seq, mask):
    """Tabular summary of each trajectory for the classical models."""
    n = mask.sum(1).astype(int)
    idx = np.arange(len(seq))
    feats = {}
    for k in range(5, T + 1, 5):                       # position every 0.5 s
        j = np.minimum(k, n) - 1
        feats[f"dx_{k}"] = seq[idx, j, 0]
        feats[f"dy_{k}"] = seq[idx, j, 1]
    last = n - 1
    prev = np.maximum(n - 6, 0)
    feats["final_dir"] = np.arctan2(seq[idx, last, 1] - seq[idx, prev, 1],
                                    seq[idx, last, 0] - seq[idx, prev, 0])
    feats["max_dx"] = seq[:, :, 0].max(1)
    feats["min_dx"] = seq[:, :, 0].min(1)
    feats["max_abs_dy"] = np.abs(seq[:, :, 1]).max(1)
    feats["max_s"] = seq[:, :, 4].max(1)
    feats["mean_s"] = (seq[:, :, 4] * mask).sum(1) / mask.sum(1)
    feats["max_a"] = seq[:, :, 5].max(1)
    steps = np.hypot(np.diff(seq[:, :, 0], axis=1), np.diff(seq[:, :, 1], axis=1))
    feats["path_len"] = (steps * mask[:, 1:]).sum(1)
    feats["t_max_depth"] = seq[:, :, 0].argmax(1) / 10
    return pd.DataFrame(feats)


# --------------------------------------------------------------- models ----

FEATURE_MODELS = {
    "En sık sınıf": lambda s: DummyClassifier(strategy="most_frequent"),
    "LogReg": lambda s: LogisticRegression(C=1.0, max_iter=3000),
    "kNN": lambda s: KNeighborsClassifier(n_neighbors=25, weights="distance", n_jobs=-1),
    "RandomForest": lambda s: RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
                                                     n_jobs=-1, random_state=s),
    "GradBoost": lambda s: HistGradientBoostingClassifier(learning_rate=0.1, max_iter=300,
                                                          max_depth=6, random_state=s),
    "MLP": lambda s: MLPClassifier(hidden_layer_sizes=(128, 64), alpha=1e-3, max_iter=300,
                                   early_stopping=True, random_state=s),
}


class RouteCNN(nn.Module):
    def __init__(self, c_in, n_cls, width=64, dropout=0.3):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(c_in, width, 5, padding=2), nn.BatchNorm1d(width), nn.ReLU(),
            nn.Conv1d(width, width, 5, padding=4, dilation=2), nn.BatchNorm1d(width), nn.ReLU(),
            nn.Conv1d(width, 2 * width, 3, padding=2, dilation=2), nn.BatchNorm1d(2 * width), nn.ReLU(),
        )
        self.head = nn.Sequential(nn.Dropout(dropout), nn.Linear(4 * width, 64), nn.ReLU(),
                                  nn.Linear(64, n_cls))

    def forward(self, x, m):
        h = self.conv(x.transpose(1, 2))
        mm = m[:, None, :]
        mean = (h * mm).sum(-1) / mm.sum(-1).clamp(min=1)
        mx = h.masked_fill(mm == 0, -1e4).max(-1).values
        return self.head(torch.cat([mean, mx], 1))


def fit_predict_cnn(seq, mask, y, tr, te, n_cls, seed, epochs=40, patience=6, batch=256):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    mu = seq[tr].reshape(-1, seq.shape[2]).mean(0)
    sd = seq[tr].reshape(-1, seq.shape[2]).std(0) + 1e-6
    X = torch.from_numpy(((seq - mu) / sd).astype(np.float32)).to(DEVICE)
    M = torch.from_numpy(mask).to(DEVICE)
    Y = torch.from_numpy(y).to(DEVICE)
    perm = rng.permutation(tr)
    n_va = int(0.1 * len(perm))
    va, trn = perm[:n_va], perm[n_va:]
    net = RouteCNN(seq.shape[2], n_cls).to(DEVICE)
    opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-3)
    loss_fn = nn.CrossEntropyLoss()
    best, state, bad = np.inf, None, 0
    va_t = torch.from_numpy(va).to(DEVICE)
    for _ in range(epochs):
        net.train()
        order = rng.permutation(trn)
        for b in range(0, len(order), batch):
            i = torch.from_numpy(order[b:b + batch]).to(DEVICE)
            opt.zero_grad()
            loss_fn(net(X[i], M[i]), Y[i]).backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            vl = loss_fn(net(X[va_t], M[va_t]), Y[va_t]).item()
        if vl < best - 1e-4:
            best, bad = vl, 0
            state = {k: v.clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    net.load_state_dict(state)
    net.eval()
    out = []
    with torch.no_grad():
        for b in range(0, len(te), 4096):
            i = torch.from_numpy(te[b:b + 4096]).to(DEVICE)
            out.append(net(X[i], M[i]).argmax(1).cpu().numpy())
    return np.concatenate(out)


def fit_predict_features(name, F, y, tr, te, seed):
    pipe = make_pipeline(StandardScaler(), FEATURE_MODELS[name](seed))
    pipe.fit(F.iloc[tr], y[tr])
    return pipe.predict(F.iloc[te])


def scores(y, p):
    return dict(macro_f1=f1_score(y, p, average="macro"), accuracy=accuracy_score(y, p))


def mcnemar(y, pa, pb):
    a_ok, b_ok = pa == y, pb == y
    n01, n10 = int((a_ok & ~b_ok).sum()), int((~a_ok & b_ok).sum())
    stat = (abs(n01 - n10) - 1) ** 2 / max(n01 + n10, 1)
    return n01, n10, stat, stats.chi2.sf(stat, 1)


# ---------------------------------------------------------------- run ----

def plot_confusion(cm, classes, path):
    cmn = cm / cm.sum(1, keepdims=True)
    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    im = ax.imshow(cmn, cmap="Blues", vmin=0, vmax=1)
    for i in range(len(classes)):
        for j in range(len(classes)):
            if cmn[i, j] >= 0.01:
                ax.text(j, i, f"{cmn[i, j]:.2f}", ha="center", va="center", fontsize=7,
                        color="white" if cmn[i, j] > 0.6 else G.TEXT)
    ax.set_xticks(range(len(classes)))
    ax.set_xticklabels(classes, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(classes)))
    ax.set_yticklabels(classes, fontsize=8)
    ax.set(xlabel="Tahmin edilen rota", ylabel="Gerçek rota")
    ax.grid(False)
    fig.colorbar(im, ax=ax, label="Satır oranı", shrink=0.8)
    ax.set_title("1D-CNN karışıklık matrisi (zaman testi, 2025)")
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def plot_examples(seq, mask, route, classes, path):
    fig, axes = plt.subplots(2, (len(classes) + 1) // 2, figsize=(12, 5.2), sharex=True, sharey=True)
    rng = np.random.default_rng(0)
    for ax, c in zip(axes.ravel(), classes):
        idx = rng.choice(np.flatnonzero(route == c), size=min(40, (route == c).sum()), replace=False)
        for i in idx:
            n = int(mask[i].sum())
            ax.plot(seq[i, :n, 1], seq[i, :n, 0], color=G.SET_COLORS["Draft"], alpha=0.25, lw=1)
        ax.set_title(c, fontsize=9)
        ax.axhline(0, color=G.NEUTRAL, lw=0.6)
    for ax in axes.ravel()[len(classes):]:
        ax.axis("off")
    fig.supxlabel("Yanal hareket (yard, + = saha merkezine doğru)", fontsize=9)
    fig.supylabel("İleri hareket (yard)", fontsize=9)
    fig.suptitle("Her rota türünden 40 örnek yol (snap'ten sonraki 3,5 sn)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main():
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    d = build_sequences()
    seq, mask, route = d["seq"], d["mask"], d["route"].copy()
    counts = pd.Series(route).value_counts()
    rare = counts[counts < MIN_CLASS].index
    route[np.isin(route, rare)] = "DİĞER"
    classes = sorted(pd.unique(route))
    y = np.array([classes.index(r) for r in route])
    F = handcrafted(seq, mask)
    print(f"{len(y)} oyun, {len(np.unique(d['nfl_id']))} oyuncu, {len(classes)} sınıf; "
          f"veri {time.time() - t0:.0f}s", flush=True)

    names = list(FEATURE_MODELS) + ["1D-CNN"]

    def run(name, tr, te, seed):
        if name == "1D-CNN":
            return fit_predict_cnn(seq, mask, y, tr, te, len(classes), seed)
        return fit_predict_features(name, F, y, tr, te, seed)

    # ---- 1. grouped 5-fold by player
    rows = []
    for fold, (tr, te) in enumerate(GroupKFold(n_splits=5).split(F, y, groups=d["nfl_id"])):
        for name in names:
            t1 = time.time()
            p = run(name, tr, te, fold)
            rows.append(dict(model=name, fold=fold, n_train=len(tr), n_test=len(te), **scores(y[te], p)))
            print(f"  katman {fold} {name:<14s} makro-F1={rows[-1]['macro_f1']:.3f} "
                  f"({time.time() - t1:.0f}s)", flush=True)
    fold_df = pd.DataFrame(rows)
    fold_df.to_csv(OUT_DIR / "katman_metrikleri.csv", index=False)
    summary = fold_df.groupby("model")[["macro_f1", "accuracy"]].agg(["mean", "std"])
    summary.columns = [f"{a}_{b}" for a, b in summary.columns]
    summary = summary.sort_values("macro_f1_mean", ascending=False)
    summary.round(4).to_csv(OUT_DIR / "ozet.csv")
    feat_models = [m for m in summary.index if m not in ("1D-CNN", "En sık sınıf")]
    best_feat = feat_models[0]
    wide = fold_df.pivot_table(index="fold", columns="model", values="macro_f1")
    tests = []
    for m in [x for x in names if x != "1D-CNN"]:
        t, p = corrected_ttest(wide["1D-CNN"], wide[m], fold_df["n_train"].mean(), fold_df["n_test"].mean())
        tests.append(dict(model=m, f1_diff_cnn_minus_model=(wide["1D-CNN"] - wide[m]).mean(),
                          t_corrected=t, p_corrected_t=p))
    tests = pd.DataFrame(tests)
    tests["p_holm"] = holm(tests["p_corrected_t"])
    tests.round(4).to_csv(OUT_DIR / "test_cnn_karsilastirma.csv", index=False)

    # ---- 2. time test: train 2023-2024, test 2025
    tr, te = np.flatnonzero(d["season"] < 2025), np.flatnonzero(d["season"] == 2025)
    p_cnn = run("1D-CNN", tr, te, 0)
    p_feat = run(best_feat, tr, te, 0)
    time_rows = [dict(model="1D-CNN", **scores(y[te], p_cnn)),
                 dict(model=best_feat, **scores(y[te], p_feat))]
    time_df = pd.DataFrame(time_rows)
    n01, n10, chi, p_mc = mcnemar(y[te], p_cnn, p_feat)
    per_class = pd.DataFrame({"rota": classes,
                              "örnek_2025": np.bincount(y[te], minlength=len(classes)),
                              "F1_CNN": f1_score(y[te], p_cnn, average=None, labels=range(len(classes))),
                              f"F1_{best_feat}": f1_score(y[te], p_feat, average=None,
                                                          labels=range(len(classes)))})
    time_df.round(4).to_csv(OUT_DIR / "zaman_testi.csv", index=False)
    per_class.round(4).to_csv(OUT_DIR / "sinif_bazinda_f1.csv", index=False)
    plot_confusion(confusion_matrix(y[te], p_cnn, labels=range(len(classes))), classes,
                   OUT_DIR / "karisiklik_matrisi.png")
    plot_examples(seq, mask, route, classes, OUT_DIR / "ornek_rotalar.png")

    cnn_better = time_df.iloc[0]["macro_f1"] > time_df.iloc[1]["macro_f1"]
    verdict = "DESTEKLENDİ" if (cnn_better and p_mc < 0.05) else "DESTEKLENMEDİ"
    md = lambda x, **k: x.to_markdown(**k)
    L = ["# C1: Maç hareket kaydından rota tanıma\n",
         "Bu dosya `ders_projesi/gorev_c1.py` tarafından otomatik üretilir. Tasarım: `TASARIM.md`.\n",
         f"- {len(y)} oyuncu-oyun, {len(np.unique(d['nfl_id']))} oyuncu, {len(classes)} sınıf "
         f"({', '.join(classes)}). 300'den az örnekli rotalar DİĞER: {', '.join(rare)}.",
         f"- Girdi: snap anından itibaren {T} kare (3,5 sn); en az {MIN_FRAMES} karesi olan kayıtlar.",
         "- İç/dış yönü saha merkezine göre yaklaşık belirlenir (hareket kaydında top konumu yok).\n",
         "![Örnek rotalar](ornek_rotalar.png)\n",
         "## 1. Oyuncuya göre gruplu 5-katlı doğrulama\n", md(summary.round(3)) + "\n",
         "### 1D-CNN ile diğer modellerin farkı (düzeltilmiş t-testi + Holm)\n",
         md(tests.round(4), index=False) + "\n",
         "## 2. Zaman testi: 2023–2024 ile eğit, 2025'te test et\n", md(time_df.round(3), index=False) + "\n",
         f"**McNemar testi** (1D-CNN ve {best_feat}): yalnız CNN doğru = {n01}, yalnız {best_feat} "
         f"doğru = {n10}, χ² = {chi:.1f}, p = {p_mc:.2e}\n",
         md(per_class.round(3), index=False) + "\n", "![Karışıklık matrisi](karisiklik_matrisi.png)\n",
         "## Hipotez H-C1\n",
         f"1D-CNN'in en iyi özellik tabanlı modelden ({best_feat}) daha yüksek makro-F1 vereceği ve "
         f"farkın zaman testinde anlamlı olacağı (McNemar p < 0.05) öngörülmüştü. Sonuç: **{verdict}**.\n",
         "## Sınırlar\n",
         "- Model yalnız tek oyuncunun hareketini görür; savunmacı ve top konumu yoktur.",
         "- Rota etiketlerinin nasıl üretildiği veri setinde açıklanmamıştır."]
    (OUT_DIR / "RAPOR.md").write_text("\n".join(L), encoding="utf-8")
    json.dump(dict(n=int(len(y)), classes=classes, best_feature_model=best_feat, verdict=verdict,
                   seconds=round(time.time() - t0)), open(OUT_DIR / "calisma.json", "w"),
              indent=2, ensure_ascii=False)
    print(summary.round(3).to_string())
    print(time_df.round(3).to_string(index=False))
    print(f"McNemar p={p_mc:.2e}  H-C1: {verdict}\nBitti: {OUT_DIR}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
