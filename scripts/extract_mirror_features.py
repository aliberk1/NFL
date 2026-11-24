"""Segment OL mirror motion from its exit sprint before outcome analysis."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/nfl-big-data-bowl-2027"
OUT = ROOT / "reports/trenches"
FEATURES = ["lateral_speed_p75", "reversal_recovery"]


def measure(g, boundary=1.5):
    g = g.sort_values("time").reset_index(drop=True)
    t = (g.time - g.time.iloc[0]).dt.total_seconds().to_numpy()
    if len(g) < 35 or np.any(np.diff(t) <= 0) or np.max(np.diff(t)) > .21:
        return None, "invalid_time_or_short", None
    x = g.x.to_numpy()
    departure = x - np.median(x[:5]) > boundary
    exits = [i for i in range(len(t) - 3) if departure[i:i + 4].all()]
    if not exits:
        return None, "no_exit", None
    end = exits[0]
    if t[end - 1] < 3:
        return None, "short_mirror", None
    mirror = g.iloc[:end]
    mt = t[:end]
    y = savgol_filter(mirror.y.to_numpy(), 5, 2)
    vy = np.gradient(y, mt)
    candidates = []
    for i in range(5, len(mt) - 6):
        if vy[i - 1] * vy[i] > 0:
            continue
        before = (mt >= mt[i] - .5 - 1e-8) & (mt <= mt[i] - .2 + 1e-8)
        after = (mt >= mt[i] + .3 - 1e-8) & (mt <= mt[i] + .6 + 1e-8)
        if abs(y[i] - y[i - 4]) < .25 or abs(y[i] - y[i + 4]) < .25:
            continue
        entry = np.mean(np.abs(vy[before]))
        if entry < .5:
            continue
        if candidates and mt[i] - mt[candidates[-1][0]] < .6:
            continue
        candidates.append((i, np.mean(np.abs(vy[after])) / entry))
    if len(candidates) < 2:
        return None, "fewer_than_two_reversals", (g, end, candidates, vy)
    smoothed_speed = g.s.rolling(3, center=True, min_periods=1).median().to_numpy()
    global_max_index = int(np.argmax(smoothed_speed))
    record = {"lateral_speed_p75": float(np.quantile(np.abs(vy), .75)),
              "reversal_recovery": float(np.median([ratio for _, ratio in candidates])),
              "whole_drill_speed": float(np.quantile(smoothed_speed, .95)),
              "mirror_duration": float(mt[-1]), "total_duration": float(t[-1]),
              "reversals": len(candidates), "peak_in_exit": bool(global_max_index >= end)}
    return record, None, (g, end, candidates, vy)


def audit_ol_drill_suite(players, raw_tracking):
    """Audit exit-sprint dominance and phase rank correlations across all three OL footwork drills."""
    ol_ids = set(players.loc[players.nfl_position.isin(["T", "G", "C"]), "nfl_id"])
    ol_track = raw_tracking.loc[raw_tracking.entity_type.eq("PLAYER") & raw_tracking.nfl_id.isin(ol_ids)].copy()
    ol_track["time"] = pd.to_datetime(ol_track.time)

    # 1. Five-Yard Wave Drill (slide and shuffle in 5-yd box followed by -x finish sprint)
    wave_rows = []
    wave_sub = ol_track.loc[ol_track.drill_name.eq("FIVE_YARD_WAVE_DRILL_SLIDE_AND_SHUFFLE")]
    for (nid, yr, eid, att), g in wave_sub.groupby(["nfl_id", "draft_year", "event_id", "attempt"]):
        g = g.sort_values("time").reset_index(drop=True)
        t = (g.time - g.time.iloc[0]).dt.total_seconds().to_numpy()
        if len(t) < 50 or np.any(np.diff(t) <= 0) or np.max(np.diff(t)) > .21:
            continue
        x = savgol_filter(g.x.to_numpy(), 5, 2)
        y = savgol_filter(g.y.to_numpy(), 5, 2)
        vy = np.gradient(y, t)
        v2d = np.hypot(np.gradient(x, t), vy)
        s_smooth = g.s.rolling(3, center=True, min_periods=1).median().to_numpy()
        x0 = np.median(x[:5])
        dep = (x0 - x) > 2.0
        exits = [i for i in range(len(t) - 3) if dep[i:i + 4].all()]
        if not exits or t[exits[0]] < 5.0:
            continue
        end = exits[0]
        wave_rows.append({
            "nfl_id": int(nid), "draft_year": int(yr), "event_id": str(eid), "attempt": int(att),
            "wave_lateral_speed_p75": float(np.quantile(np.abs(vy[:end]), .75)),
            "wave_shuffle_speed_p75": float(np.quantile(v2d[:end], .75)),
            "wave_whole_speed_p95": float(np.quantile(s_smooth, .95)),
            "wave_peak_in_exit": bool(int(np.argmax(s_smooth)) >= end),
        })
    wave_df = pd.DataFrame(wave_rows)

    # 2. Pass Rush Drop (diagonal kick-slide drop followed by -x finish sprint; 2 attempts per player)
    drop_rows = []
    drop_sub = ol_track.loc[ol_track.drill_name.eq("PASS_RUSH_DROP")]
    for (nid, yr, eid, att), g in drop_sub.groupby(["nfl_id", "draft_year", "event_id", "attempt"]):
        g = g.sort_values("time").reset_index(drop=True)
        t = (g.time - g.time.iloc[0]).dt.total_seconds().to_numpy()
        if len(t) < 25 or np.any(np.diff(t) <= 0) or np.max(np.diff(t)) > .21:
            continue
        x = savgol_filter(g.x.to_numpy(), 5, 2)
        y = savgol_filter(g.y.to_numpy(), 5, 2)
        vx = np.gradient(x, t)
        vy = np.gradient(y, t)
        v2d = np.hypot(vx, vy)
        s_smooth = g.s.rolling(3, center=True, min_periods=1).median().to_numpy()
        dep = np.abs(x - x[0]) > 2.2
        exits = [i for i in range(len(t) - 3) if dep[i:i + 4].all()]
        if not exits or exits[0] < 8:
            continue
        end = exits[0]
        drop_rows.append({
            "nfl_id": int(nid), "draft_year": int(yr), "event_id": str(eid), "attempt": int(att),
            "drop_lateral_speed_p75": float(np.quantile(np.abs(vy[:end]), .75)),
            "drop_depth_speed_p75": float(np.quantile(np.abs(vx[:end]), .75)),
            "drop_2d_speed_p75": float(np.quantile(v2d[:end], .75)),
            "drop_whole_speed_p95": float(np.quantile(s_smooth, .95)),
            "drop_peak_in_exit": bool(int(np.argmax(s_smooth)) >= end),
        })
    drop_df = pd.DataFrame(drop_rows).sort_values(["nfl_id", "attempt", "event_id"])
    drop_df["rep"] = drop_df.groupby("nfl_id").cumcount()
    drop_piv = drop_df.loc[drop_df.rep.lt(2)].pivot(index="nfl_id", columns="rep")
    repeatability = {}
    for col in ["drop_whole_speed_p95", "drop_lateral_speed_p75", "drop_depth_speed_p75", "drop_2d_speed_p75"]:
        valid = drop_piv[col].dropna()
        repeatability[col] = {
            "paired_players": int(len(valid)),
            "pearson_r": float(valid[0].corr(valid[1])),
            "spearman_r": float(valid[0].corr(valid[1], method="spearman")),
        }
    drop_player = drop_df.groupby("nfl_id")[["drop_lateral_speed_p75", "drop_depth_speed_p75",
                                             "drop_2d_speed_p75", "drop_whole_speed_p95"]].median()
    return wave_df, drop_df, drop_player, repeatability


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    players = pd.read_csv(DATA / "players.csv")
    ol = players.loc[players.nfl_position.isin(["T", "G", "C"])]
    raw_tracking = pd.read_csv(DATA / "combine_tracking.csv")
    tracking = raw_tracking.loc[raw_tracking.entity_type.eq("PLAYER") & raw_tracking.nfl_id.isin(ol.nfl_id) &
                                raw_tracking.drill_name.isin(["PASS_PRO-MIRROR_DRILL", "PASS_PRO_MIRROR_DRILL"])].copy()
    tracking["time"] = pd.to_datetime(tracking.time)
    results, rejected, details = [], [], {}
    sensitivity = []
    for key, g in tracking.groupby(["nfl_id", "draft_year", "event_id", "attempt"]):
        ids = dict(zip(["nfl_id", "draft_year", "event_id", "attempt"], key))
        result, reason, detail = measure(g)
        if reason:
            rejected.append({**ids, "reason": reason})
        else:
            results.append({**ids, **result})
            details[key] = detail
        for boundary in (1.0, 2.0):
            alternative, reason, _ = measure(g, boundary)
            if alternative:
                sensitivity.append({**ids, "boundary": boundary, **alternative})
    attempts = pd.DataFrame(results)
    attempts.to_csv(OUT / "mirror_attempt_features.csv", index=False)
    pd.DataFrame(rejected).to_csv(OUT / "mirror_rejected.csv", index=False)
    pd.DataFrame(sensitivity).to_csv(OUT / "mirror_boundary_sensitivity.csv", index=False)
    feature = attempts.groupby("nfl_id")[FEATURES + ["whole_drill_speed", "mirror_duration", "peak_in_exit"]].median()
    feature.to_csv(OUT / "mirror_player_features.csv")

    wave_df, drop_df, drop_player, drop_repeatability = audit_ol_drill_suite(players, raw_tracking)
    suite_summary = pd.DataFrame([
        {
            "drill": "Pass-Pro Mirror Drill",
            "accepted_attempts": int(len(attempts)),
            "accepted_players": int(attempts.nfl_id.nunique()),
            "peak_in_exit_fraction": float(attempts.peak_in_exit.mean()),
            "phase_vs_whole_spearman": float(attempts.lateral_speed_p75.corr(attempts.whole_drill_speed, method="spearman")),
        },
        {
            "drill": "5-Yard Wave Drill (Slide & Shuffle)",
            "accepted_attempts": int(len(wave_df)),
            "accepted_players": int(wave_df.nfl_id.nunique()),
            "peak_in_exit_fraction": float(wave_df.wave_peak_in_exit.mean()),
            "phase_vs_whole_spearman": float(wave_df.wave_lateral_speed_p75.corr(wave_df.wave_whole_speed_p95, method="spearman")),
        },
        {
            "drill": "Pass Rush Drop (Kick-Slide)",
            "accepted_attempts": int(len(drop_df)),
            "accepted_players": int(drop_df.nfl_id.nunique()),
            "peak_in_exit_fraction": float(drop_df.drop_peak_in_exit.mean()),
            "phase_vs_whole_spearman": float(drop_player.drop_lateral_speed_p75.corr(drop_player.drop_whole_speed_p95, method="spearman")),
        },
    ])
    suite_summary.to_csv(OUT / "ol_drill_suite_audit.csv", index=False)

    audit = {"raw_players": tracking.nfl_id.nunique(), "accepted_players": len(feature),
             "accepted_attempts": len(attempts), "rejected_attempts": len(rejected),
             "peak_in_exit_fraction": float(attempts.peak_in_exit.mean()),
             "by_year": attempts.groupby("draft_year").agg(players=("nfl_id", "nunique"),
                 peak_in_exit_fraction=("peak_in_exit", "mean"), duration=("mirror_duration", "median")).reset_index().to_dict("records"),
             "boundary_rank_correlations": [],
             "ol_drill_suite_audit": suite_summary.to_dict("records"),
             "pass_rush_drop_repeatability": drop_repeatability}
    for boundary in (1.0, 2.0):
        alternative = pd.DataFrame(sensitivity)
        alternative = alternative.loc[alternative.boundary.eq(boundary)]
        paired = attempts.merge(alternative, on=["nfl_id", "draft_year", "event_id", "attempt"], suffixes=("_main", "_alt"))
        audit["boundary_rank_correlations"].append({"boundary": boundary, "paired_attempts": len(paired),
            **{name: float(paired[name + "_main"].corr(paired[name + "_alt"], method="spearman")) for name in FEATURES}})
    # Review all accepted attempts in a multipage PDF; a nine-example PNG is also saved.
    from matplotlib.backends.backend_pdf import PdfPages
    with PdfPages(OUT / "mirror_all_phase_checks.pdf") as pdf:
        entries = list(details.items())
        for offset in range(0, len(entries), 12):
            fig, axes = plt.subplots(3, 4, figsize=(13, 10))
            for ax in axes.flat:
                ax.set_visible(False)
            for ax, (key, (g, end, turns, vy)) in zip(axes.flat, entries[offset:offset + 12]):
                ax.set_visible(True)
                ax.plot(g.x.iloc[:end], g.y.iloc[:end], color="#176b87", label="Mirror")
                ax.plot(g.x.iloc[end - 1:], g.y.iloc[end - 1:], color="#e99b37", label="Exit")
                if turns:
                    idx = [i for i, _ in turns]
                    ax.scatter(g.x.iloc[idx], g.y.iloc[idx], color="#b43b45", s=18)
                ax.set_title(f"{key[1]} {ol.set_index('nfl_id').loc[key[0], 'display_name']}", fontsize=9)
                ax.set_aspect("equal", adjustable="datalim")
            axes.flat[0].legend(fontsize=7)
            fig.suptitle("Mirror phase (blue), exit sprint (orange), detected reversals (red)")
            fig.tight_layout()
            pdf.savefig(fig)
            if offset == 0:
                fig.savefig(OUT / "mirror_phase_examples.png", dpi=140)
            plt.close(fig)
    (OUT / "mirror_feature_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
