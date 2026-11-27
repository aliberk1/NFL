"""Cross-validation protocol, metrics and statistical comparison of models."""
import time

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import (average_precision_score, brier_score_loss, log_loss,
                             mean_absolute_error, mean_squared_error, r2_score, roc_auc_score)
from sklearn.model_selection import RepeatedStratifiedKFold


def metrics(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return dict(auc=roc_auc_score(y, p), ap=average_precision_score(y, p),
                brier=brier_score_loss(y, p), logloss=log_loss(y, p))


def metrics_reg(y, p):
    return dict(r2=r2_score(y, p), mae=mean_absolute_error(y, p),
                rmse=float(np.sqrt(mean_squared_error(y, p))),
                spearman=stats.spearmanr(y, p)[0])


def cv_splits(strata, n_splits=5, n_repeats=5, seed=42):
    rskf = RepeatedStratifiedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=seed)
    return [(r // n_splits, r % n_splits, tr, te)
            for r, (tr, te) in enumerate(rskf.split(np.zeros(len(strata)), strata))]


def run_cv(factories, ctx, splits, log=print, metric_fn=None, key="auc"):
    """factories: {name: callable(seed) -> model}. Same splits for every model."""
    metric_fn = metric_fn or metrics
    y = ctx["y"]
    n_rep = max(s[0] for s in splits) + 1
    rows, oof = [], {}
    for name, make in factories.items():
        t0 = time.time()
        pred = np.full((n_rep, len(y)), np.nan)
        for rep, fold, tr, te in splits:
            model = make(seed=rep * 100 + fold).fit(ctx, tr)
            p = model.predict(ctx, te)
            pred[rep, te] = p
            rows.append(dict(model=name, repeat=rep, fold=fold, n_train=len(tr),
                             n_test=len(te), **metric_fn(y[te], p)))
        oof[name] = pred
        score = np.mean([r[key] for r in rows if r["model"] == name])
        log(f"  {name:<40s} {key.upper()}={score:.3f}  ({time.time() - t0:.0f}s)")
    return pd.DataFrame(rows), oof


def run_leave_cohort_out(factories, ctx, cohort, log=print):
    """Train on two draft classes, test on the third."""
    y, rows = ctx["y"], []
    for c in np.unique(cohort):
        tr, te = np.where(cohort != c)[0], np.where(cohort == c)[0]
        for name, make in factories.items():
            p = make(seed=int(c)).fit(ctx, tr).predict(ctx, te)
            rows.append(dict(model=name, test_cohort=int(c), **metrics(y[te], p)))
    return pd.DataFrame(rows)


def summarize(fold_df, cols=("auc", "ap", "brier", "logloss"), key="auc"):
    agg = fold_df.groupby("model")[list(cols)].agg(["mean", "std"])
    agg.columns = [f"{m}_{s}" for m, s in agg.columns]
    return agg.sort_values(f"{key}_mean", ascending=False)


def bootstrap_ci(y, p, n_boot=2000, seed=0, metric=roc_auc_score):
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() == y[i].max():
            continue
        vals.append(metric(y[i], p[i]))
    return np.percentile(vals, [2.5, 97.5])


def paired_bootstrap_diff(y, p_a, p_b, n_boot=2000, seed=0, metric=roc_auc_score):
    """metric(a) - metric(b) on the same units: point estimate, 95% CI, two-sided p."""
    rng = np.random.default_rng(seed)
    d0 = metric(y, p_a) - metric(y, p_b)
    ds = []
    for _ in range(n_boot):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() == y[i].max():
            continue
        ds.append(metric(y[i], p_a[i]) - metric(y[i], p_b[i]))
    ds = np.array(ds)
    p = 2 * min((ds <= 0).mean(), (ds >= 0).mean())
    lo, hi = np.percentile(ds, [2.5, 97.5])
    return d0, lo, hi, min(p, 1.0)


def corrected_ttest(a, b, n_train, n_test):
    """Nadeau & Bengio (2003) corrected resampled t-test on per-fold scores."""
    d = np.asarray(a) - np.asarray(b)
    J = len(d)
    var = d.var(ddof=1)
    if var == 0:
        return 0.0, 1.0
    t = d.mean() / np.sqrt((1 / J + n_test / n_train) * var)
    return t, 2 * stats.t.sf(abs(t), df=J - 1)


def holm(pvals):
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for k, i in enumerate(order):
        running = max(running, (len(p) - k) * p[i])
        adj[i] = min(running, 1.0)
    return adj


def compare_to_reference(fold_df, oof, y, reference, key="auc", metric=roc_auc_score):
    """Every model against `reference`: corrected t-test on fold scores + paired bootstrap."""
    wide = fold_df.pivot_table(index=["repeat", "fold"], columns="model", values=key)
    n_train, n_test = fold_df["n_train"].mean(), fold_df["n_test"].mean()
    ref_p = np.nanmean(oof[reference], axis=0)
    rows = []
    for m in wide.columns:
        if m == reference:
            continue
        t, p_t = corrected_ttest(wide[m], wide[reference], n_train, n_test)
        d, lo, hi, p_b = paired_bootstrap_diff(y, np.nanmean(oof[m], axis=0), ref_p, metric=metric)
        rows.append(dict(model=m, reference=reference, auc_diff_folds=(wide[m] - wide[reference]).mean(),
                         t_corrected=t, p_corrected_t=p_t, auc_diff_oof=d,
                         ci_low=lo, ci_high=hi, p_bootstrap=p_b))
    out = pd.DataFrame(rows)
    out["p_holm"] = holm(out["p_corrected_t"])
    out = out.sort_values("auc_diff_folds", ascending=False)
    if key != "auc":
        out.columns = [c.replace("auc_", f"{key}_") for c in out.columns]
    return out


def friedman(fold_df, models, key="auc"):
    wide = fold_df[fold_df["model"].isin(models)].pivot_table(
        index=["repeat", "fold"], columns="model", values=key)
    stat, p = stats.friedmanchisquare(*[wide[m] for m in wide.columns])
    ranks = wide.rank(axis=1, ascending=False).mean().sort_values()
    return stat, p, ranks
