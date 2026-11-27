"""Feature builders: tabular combine features, tracking summaries and raw sequences."""
import numpy as np
import pandas as pd

from .veri import COMBINE_MEASURES, OUT, read

CACHE = OUT / "cache"
MAX_LEN = 200          # frames (10 Hz) kept per drill attempt
SEQ_CHANNELS = ["s", "a", "turn", "cum_dis"]
ATTEMPT_KEY = ["nfl_id", "event_id", "drill_name", "attempt"]


def _attempt_frames():
    """Player rows of combine_tracking sorted in time, with a turn-rate channel."""
    ct = read("combine_tracking.csv")
    ct = ct[ct["entity_type"] == "PLAYER"].copy()
    ct["t"] = pd.to_datetime(ct["time"])
    ct = ct.sort_values(ATTEMPT_KEY + ["t"]).reset_index(drop=True)
    g = ct.groupby(ATTEMPT_KEY, sort=False)
    d_dir = g["dir"].diff().fillna(0.0)
    d_dir = (d_dir + 180) % 360 - 180               # wrap to [-180, 180)
    ct["turn"] = (d_dir.abs() * 10).where(ct["s"] > 1.0, 0.0)  # deg/s while moving
    ct["cum_dis"] = g["dis"].cumsum()
    ct["frame"] = g.cumcount()
    return ct


def tracking_summary(ct=None):
    """Player-level summary of combine tracking (one row per nfl_id)."""
    ct = _attempt_frames() if ct is None else ct
    att = ct.groupby(ATTEMPT_KEY).agg(
        drill_type=("drill_type", "first"),
        peak_s=("s", "max"), peak_a=("a", "max"), mean_s=("s", "mean"),
        duration=("frame", "size"), mean_turn=("turn", "mean"),
    ).reset_index()
    att["duration"] = att["duration"] / 10.0
    # Standardise within each drill so different drills can be pooled.
    for col in ["peak_s", "peak_a", "mean_s", "duration", "mean_turn"]:
        grp = att.groupby("drill_name")[col]
        att[col + "_z"] = (att[col] - grp.transform("mean")) / grp.transform("std").replace(0, np.nan)
    att["duration_z"] = -att["duration_z"]          # shorter is better
    # Best attempt per player and drill, then average across that player's drills.
    best = att.groupby(["nfl_id", "drill_name"])[
        ["peak_s_z", "peak_a_z", "mean_s_z", "duration_z", "mean_turn_z"]].max()
    out = best.groupby("nfl_id").mean().add_prefix("trk_")
    out["trk_n_drills"] = best.groupby("nfl_id").size()
    out["trk_n_attempts"] = att.groupby("nfl_id").size()
    # Raw physical values in the drills every position runs.
    for drill, tag in [("FORTY_YARD_DASH", "forty"), ("THREE_CONE_DRILL", "cone"),
                       ("SHORT_SHUTTLE", "shuttle")]:
        sub = att[att["drill_name"] == drill].groupby("nfl_id")
        out[f"trk_{tag}_peak_s"] = sub["peak_s"].max()
        out[f"trk_{tag}_peak_a"] = sub["peak_a"].max()
    return out.reset_index()


def build_sequences(player_ids, ct=None):
    """Raw per-attempt sequences for the CNN.

    Returns dict with seq [N_att, MAX_LEN, C], mask [N_att, MAX_LEN], drill [N_att],
    owner [N_att] (row index in player_ids) and drill vocabulary.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "combine_sequences.npz"
    if path.exists():
        z = np.load(path, allow_pickle=True)
        if np.array_equal(z["player_ids"], np.asarray(player_ids)):
            return {k: z[k] for k in z.files}
    ct = _attempt_frames() if ct is None else ct
    ct = ct[ct["frame"] < MAX_LEN]
    vocab = np.array(sorted(ct["drill_name"].unique()))
    drill_index = {d: i for i, d in enumerate(vocab)}
    pid_index = {p: i for i, p in enumerate(player_ids)}
    groups = list(ct.groupby(ATTEMPT_KEY, sort=True))
    n = len(groups)
    seq = np.zeros((n, MAX_LEN, len(SEQ_CHANNELS)), dtype=np.float32)
    mask = np.zeros((n, MAX_LEN), dtype=np.float32)
    drill = np.zeros(n, dtype=np.int64)
    owner = np.full(n, -1, dtype=np.int64)
    for i, ((pid, _, dname, _), g) in enumerate(groups):
        L = len(g)
        seq[i, :L] = g[SEQ_CHANNELS].to_numpy(np.float32)
        mask[i, :L] = 1.0
        drill[i] = drill_index[dname]
        owner[i] = pid_index.get(pid, -1)
    keep = owner >= 0
    seq, mask, drill, owner = seq[keep], mask[keep], drill[keep], owner[keep]
    # Global channel scaling over valid frames (no labels involved).
    valid = mask.astype(bool)
    mu = seq[valid].mean(axis=0)
    sd = seq[valid].std(axis=0) + 1e-6
    seq = np.where(valid[..., None], (seq - mu) / sd, 0.0).astype(np.float32)
    out = dict(seq=seq, mask=mask, drill=drill, owner=owner, vocab=vocab,
               player_ids=np.asarray(player_ids))
    np.savez_compressed(path, **out)
    return out


def tabular_feature_sets(df):
    """Column lists for each feature set compared in Task A."""
    draft = ["log_pick", "undrafted", "round_filled"]
    context = ["age_at_draft", "cohort_2024", "cohort_2025"] + [
        f"pos_{g}" for g in ["OL", "DL", "LB", "DB", "WR", "TE"]]
    combine = COMBINE_MEASURES + ["bmi", "speed_score", "ngs_athleticism_score"]
    tracking = [c for c in df.columns if c.startswith("trk_")]
    return {
        "draft": draft,
        "combine": context + combine,
        "combine_trk": context + combine + tracking,
        "combine_trk_draft": context + combine + tracking + draft,
    }


def add_dummies(df):
    df = df.copy()
    for g in ["OL", "DL", "LB", "DB", "WR", "TE"]:
        df[f"pos_{g}"] = (df["position_group"] == g).astype(int)
    df["cohort_2024"] = (df["draft_year"] == 2024).astype(int)
    df["cohort_2025"] = (df["draft_year"] == 2025).astype(int)
    return df
