"""Model registry with a shared fit(ctx, idx) / predict(ctx, idx) interface.

ctx is a dict: X (DataFrame of tabular features), y (np.ndarray), seq (sequence dict).
"""
import numpy as np
import torch
from torch import nn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

torch.set_num_threads(4)
DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")


def _prep():
    return [SimpleImputer(strategy="median", add_indicator=True), StandardScaler()]


SKLEARN = {
    "Dummy": lambda s: DummyClassifier(strategy="prior"),
    "LogReg": lambda s: LogisticRegression(C=0.3, max_iter=2000),
    "kNN": lambda s: KNeighborsClassifier(n_neighbors=25, weights="distance"),
    "SVM": lambda s: SVC(C=1.0, kernel="rbf", probability=True, random_state=s),
    "RandomForest": lambda s: RandomForestClassifier(
        n_estimators=500, min_samples_leaf=3, max_features="sqrt", n_jobs=-1, random_state=s),
    "GradBoost": lambda s: HistGradientBoostingClassifier(
        learning_rate=0.05, max_depth=3, max_iter=200, l2_regularization=1.0,
        min_samples_leaf=15, random_state=s),
    "MLP": lambda s: MLPClassifier(hidden_layer_sizes=(32,), alpha=1.0, max_iter=2000,
                                   early_stopping=True, validation_fraction=0.15,
                                   random_state=s),
}


class SkModel:
    def __init__(self, algo, cols, seed=0):
        self.name, self.algo, self.cols, self.seed = algo, algo, list(cols), seed

    def fit(self, ctx, idx):
        self.pipe = make_pipeline(*_prep(), SKLEARN[self.algo](self.seed))
        self.pipe.fit(ctx["X"].iloc[idx][self.cols], ctx["y"][idx])
        return self

    def predict(self, ctx, idx):
        return self.pipe.predict_proba(ctx["X"].iloc[idx][self.cols])[:, 1]


# ------------------------------------------------------------ regression ----

from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.svm import SVR

SKLEARN_REG = {
    "Ortalama": lambda s: DummyRegressor(strategy="mean"),
    "Ridge": lambda s: Ridge(alpha=3.0),
    "kNN": lambda s: KNeighborsRegressor(n_neighbors=25, weights="distance"),
    "SVR": lambda s: SVR(C=1.0, epsilon=0.1),
    "RandomForest": lambda s: RandomForestRegressor(
        n_estimators=500, min_samples_leaf=3, max_features="sqrt", n_jobs=-1, random_state=s),
    "GradBoost": lambda s: HistGradientBoostingRegressor(
        learning_rate=0.05, max_depth=3, max_iter=200, l2_regularization=1.0,
        min_samples_leaf=15, random_state=s),
    "MLP": lambda s: MLPRegressor(hidden_layer_sizes=(32,), alpha=1.0, max_iter=3000,
                                  early_stopping=True, validation_fraction=0.15, random_state=s),
}


class SkRegModel:
    """Regression on a standardised target (SVR/MLP/kNN need a scaled y)."""

    def __init__(self, algo, cols, seed=0):
        self.name, self.algo, self.cols, self.seed = algo, algo, list(cols), seed

    def fit(self, ctx, idx):
        y = ctx["y"][idx].astype(float)
        self.mu, self.sd = y.mean(), y.std() + 1e-9
        self.pipe = make_pipeline(*_prep(), SKLEARN_REG[self.algo](self.seed))
        self.pipe.fit(ctx["X"].iloc[idx][self.cols], (y - self.mu) / self.sd)
        return self

    def predict(self, ctx, idx):
        return self.pipe.predict(ctx["X"].iloc[idx][self.cols]) * self.sd + self.mu


# ---------------------------------------------------------------- 1D-CNN ----

class AttemptEncoder(nn.Module):
    """1D-CNN over one drill attempt (time x channels) -> fixed embedding."""

    def __init__(self, n_channels, n_drills, emb=8, width=32, out=32, dropout=0.2):
        super().__init__()
        self.drill_emb = nn.Embedding(n_drills, emb)
        self.conv = nn.Sequential(
            nn.Conv1d(n_channels + emb, width, 5, padding=2), nn.BatchNorm1d(width), nn.ReLU(),
            nn.Conv1d(width, width, 5, padding=4, dilation=2), nn.BatchNorm1d(width), nn.ReLU(),
            nn.Conv1d(width, 2 * width, 3, padding=1), nn.ReLU(),
        )
        self.proj = nn.Sequential(nn.Dropout(dropout), nn.Linear(4 * width, out), nn.ReLU())

    def forward(self, seq, mask, drill):
        # seq [A, T, C], mask [A, T], drill [A]
        e = self.drill_emb(drill)[:, :, None].expand(-1, -1, seq.shape[1])
        h = self.conv(torch.cat([seq.transpose(1, 2), e], dim=1))      # [A, F, T]
        m = mask[:, None, :]
        mean = (h * m).sum(-1) / m.sum(-1).clamp(min=1)
        mx = h.masked_fill(m == 0, -1e4).max(-1).values
        return self.proj(torch.cat([mean, mx], dim=1))


class PlayerNet(nn.Module):
    """Encodes a player's valid attempts and mean-pools them; optional tabular join."""

    def __init__(self, n_channels, n_drills, n_tab=0, emb_out=32, dropout=0.3):
        super().__init__()
        self.enc = AttemptEncoder(n_channels, n_drills, out=emb_out)
        self.head = nn.Sequential(
            nn.Linear(emb_out + n_tab, 32), nn.ReLU(), nn.Dropout(dropout), nn.Linear(32, 1))

    def forward(self, seq, mask, drill, att_mask, tab=None):
        # seq [B, A, T, C], mask [B, A, T], drill [B, A], att_mask [B, A]
        B, A, T, C = seq.shape
        valid = att_mask.reshape(-1) > 0
        z_valid = self.enc(seq.reshape(B * A, T, C)[valid], mask.reshape(B * A, T)[valid],
                           drill.reshape(-1)[valid])
        z = torch.zeros(B * A, z_valid.shape[1], device=seq.device)
        z[valid] = z_valid
        z = z.reshape(B, A, -1)
        pooled = (z * att_mask[..., None]).sum(1) / att_mask.sum(1, keepdim=True).clamp(min=1)
        if tab is not None:
            pooled = torch.cat([pooled, tab], dim=1)
        return self.head(pooled).squeeze(1)


class CNNModel:
    """Set-of-sequences CNN. tab_cols=None -> tracking only; else hybrid."""

    def __init__(self, name, tab_cols=None, seed=0, epochs=80, batch=32, lr=2e-3,
                 weight_decay=1e-3, patience=12, max_len=160):
        self.name, self.tab_cols, self.seed = name, tab_cols, seed
        self.epochs, self.batch, self.lr = epochs, batch, lr
        self.wd, self.patience, self.max_len = weight_decay, patience, max_len

    def _device_cache(self, ctx):
        """Pack attempts into a [players, max_attempts, T, C] tensor on the device once."""
        key = f"_dev{self.max_len}"
        if key not in ctx:
            s, T = ctx["seq"], self.max_len
            n = len(ctx["y"])
            counts = np.bincount(s["owner"], minlength=n)
            A = int(counts.max())
            P = np.zeros((n, A, T, s["seq"].shape[2]), np.float32)
            M = np.zeros((n, A, T), np.float32)
            D = np.zeros((n, A), np.int64)
            AM = np.zeros((n, A), np.float32)
            slot = np.zeros(n, np.int64)
            for i, o in enumerate(s["owner"]):
                k = slot[o]
                P[o, k], M[o, k], D[o, k], AM[o, k] = s["seq"][i, :T], s["mask"][i, :T], s["drill"][i], 1
                slot[o] += 1
            ctx[key] = [torch.from_numpy(x).to(DEVICE) for x in (P, M, D, AM)]
        return ctx[key]

    def _forward(self, ctx, players, train, tab=None):
        self.net.train(train)
        P, M, D, AM = self._device_cache(ctx)
        i = torch.from_numpy(np.asarray(players)).to(DEVICE)
        return self.net(P[i], M[i], D[i], AM[i], tab)

    def fit(self, ctx, idx):
        torch.manual_seed(self.seed)
        rng = np.random.default_rng(self.seed)
        y = ctx["y"]
        tr, va = train_test_split(idx, test_size=0.15, stratify=y[idx], random_state=self.seed)
        n_tab = 0
        if self.tab_cols is not None:
            self.prep = make_pipeline(*_prep()).fit(ctx["X"].iloc[tr][self.tab_cols])
            n_tab = self.prep.transform(ctx["X"].iloc[tr[:2]][self.tab_cols]).shape[1]
        tab_all = None
        if self.tab_cols is not None:
            tab_all = torch.from_numpy(
                self.prep.transform(ctx["X"][self.tab_cols]).astype(np.float32)).to(DEVICE)
        self.tab_all = tab_all
        n_drills = len(ctx["seq"]["vocab"])
        self.net = PlayerNet(ctx["seq"]["seq"].shape[2], n_drills, n_tab).to(DEVICE)
        opt = torch.optim.AdamW(self.net.parameters(), lr=self.lr, weight_decay=self.wd)
        loss_fn = nn.BCEWithLogitsLoss()
        best, best_state, bad = np.inf, None, 0
        yv = torch.tensor(y[va], dtype=torch.float32, device=DEVICE)
        for _ in range(self.epochs):
            order = rng.permutation(tr)
            for b in range(0, len(order), self.batch):
                pl = order[b:b + self.batch]
                if len(pl) < 2:
                    continue
                opt.zero_grad()
                loss = loss_fn(self._forward(ctx, pl, True, self._tab_rows(pl)),
                               torch.tensor(y[pl], dtype=torch.float32, device=DEVICE))
                loss.backward()
                opt.step()
            with torch.no_grad():
                vl = loss_fn(self._forward(ctx, va, False, self._tab_rows(va)), yv).item()
            if vl < best - 1e-4:
                best, bad = vl, 0
                best_state = {k: v.clone() for k, v in self.net.state_dict().items()}
            else:
                bad += 1
                if bad >= self.patience:
                    break
        self.net.load_state_dict(best_state)
        return self

    def predict(self, ctx, idx):
        with torch.no_grad():
            idx = np.asarray(idx)
            return torch.sigmoid(self._forward(ctx, idx, False, self._tab_rows(idx))).cpu().numpy()

    def _tab_rows(self, players):
        if self.tab_all is None:
            return None
        return self.tab_all[torch.from_numpy(np.asarray(players)).to(DEVICE)]
