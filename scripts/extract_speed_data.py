"""Extract WR Combine and rookie pre-throw route speed with explicit QA."""
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/nfl-big-data-bowl-2027"
OUT = ROOT / "data/processed"
REPORT = ROOT / "reports/speed_study"
KEYS = ["game_id", "play_id", "nfl_id"]


def combine_features(players):
    tracking = pd.read_csv(DATA / "combine_tracking.csv")
    tracking = tracking.loc[tracking.entity_type.eq("PLAYER") &
                            tracking.nfl_id.isin(players.nfl_id) &
                            tracking.drill_name.eq("FORTY_YARD_DASH")].copy()
    tracking["time"] = pd.to_datetime(tracking.time)
    output, rejected = [], []
    for key, g in tracking.groupby(["nfl_id", "event_id", "attempt"]):
        g = g.sort_values("time")
        t = (g.time - g.time.iloc[0]).dt.total_seconds().to_numpy()
        s = g.s.rolling(3, center=True, min_periods=1).median().to_numpy()
        onset = np.flatnonzero(s >= 1)
        reason = None
        if len(g) < 20 or not len(onset) or not np.isfinite(s).all() or (s < 0).any():
            reason = "invalid_or_short"
        elif np.any(np.diff(t) <= 0) or np.max(np.diff(t)) > .21:
            reason = "duplicate_time_or_gap"
        elif t[onset[0]] + 1 > t[-1]:
            reason = "short_onset_window"
        if reason:
            rejected.append({"nfl_id": key[0], "event_id": key[1], "attempt": key[2], "reason": reason})
            continue
        coordinate_speed = np.linalg.norm(np.diff(g[["x", "y"]].to_numpy(), axis=0), axis=1) / np.diff(t)
        mask = s[1:] > 2
        output.append({"nfl_id": key[0], "event_id": key[1], "attempt": key[2],
                       "combine_peak_speed": float(np.quantile(s, .95)),
                       "combine_early_speed": float(np.interp(t[onset[0]] + 1, t, s)),
                       "initial_speed": float(g.s.iloc[0]),
                       "onset_already_above_threshold": bool(g.s.iloc[0] >= 1),
                       "duration": t[-1],
                       "coordinate_to_s_ratio": float(np.median(coordinate_speed[mask] / s[1:][mask]))})
    frame = pd.DataFrame(output)
    frame.to_csv(OUT / "combine_speed_attempts.csv", index=False)
    pd.DataFrame(rejected).to_csv(REPORT / "combine_rejected.csv", index=False)
    frame.groupby("nfl_id")[["combine_peak_speed", "combine_early_speed"]].median().to_csv(
        OUT / "combine_speed_players.csv")
    return {"attempts": len(frame), "players": frame.nfl_id.nunique(), "rejected": len(rejected),
            "onset_already_above_threshold_attempts": int(frame.onset_already_above_threshold.sum()),
            "coordinate_to_s_ratio_median": frame.coordinate_to_s_ratio.median()}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    players = pd.read_csv(DATA / "players.csv")
    players = players.loc[players.nfl_position.eq("WR")]
    combine_qa = combine_features(players)
    games = pd.read_csv(DATA / "games.csv")
    cols = KEYS + ["route_ran", "team_coverage_man_zone", "cushion", "play_nullified_by_penalty"]
    metadata = pd.read_csv(DATA / "player_play.csv", usecols=cols)
    assert not metadata.duplicated(KEYS).any(), "Duplicate player-play metadata"
    metadata = metadata.merge(players[["nfl_id", "draft_year"]], on="nfl_id", validate="many_to_one")
    metadata = metadata.merge(games[["game_id", "season", "season_type"]], on="game_id", validate="many_to_one")
    metadata = metadata.loc[metadata.season_type.eq("REG") & metadata.season.eq(metadata.draft_year) &
                            metadata.play_nullified_by_penalty.eq("N") & metadata.route_ran.notna()]
    all_output, year_audits, rejected = [], [], []
    for year in (2023, 2024, 2025):
        year_meta = metadata.loc[metadata.season.eq(year)].copy()
        wanted = pd.MultiIndex.from_frame(year_meta[KEYS])
        frames, scanned, events = [], 0, Counter()
        for chunk in pd.read_csv(DATA / f"game_tracking_{year}.csv",
                                 usecols=KEYS + ["time", "s", "x", "y", "event"], chunksize=300000):
            scanned += len(chunk)
            chunk = chunk.loc[chunk.nfl_id.isin(year_meta.nfl_id)]
            chunk = chunk.loc[pd.MultiIndex.from_frame(chunk[KEYS]).isin(wanted)].copy()
            if len(chunk):
                frames.append(chunk)
                events.update(chunk.event.dropna().value_counts().to_dict())
        selected = pd.concat(frames, ignore_index=True)
        selected["time"] = pd.to_datetime(selected.time)
        counts = Counter()
        tracked_keys = pd.MultiIndex.from_frame(selected[KEYS].drop_duplicates())
        missing = year_meta.loc[~pd.MultiIndex.from_frame(year_meta[KEYS]).isin(tracked_keys)]
        counts["missing_tracking"] = len(missing)
        for row in missing[KEYS].to_dict("records"):
            rejected.append({**row, "season": year, "reason": "missing_tracking"})
        coordinate_ratios = []
        for key, g in selected.groupby(KEYS, sort=False):
            g = g.sort_values("time")
            snaps = g.loc[g.event.eq("ball_snap"), "time"]
            throws = g.loc[g.event.eq("pass_forward"), "time"]
            reason = None
            if len(snaps) != 1 or len(throws) != 1:
                reason = "missing_or_multiple_snap_throw"
            elif g.time.duplicated().any():
                reason = "duplicate_frame_time"
            if reason:
                counts[reason] += 1
                rejected.append(dict(zip(KEYS, key), season=year, reason=reason))
                continue
            start, throw = snaps.iloc[0], throws.iloc[0]
            end = min(throw, start + pd.Timedelta(seconds=4))
            live = g.loc[g.time.ge(start) & g.time.le(end)].copy()
            duration = (end - start).total_seconds()
            if duration < 2 or len(live) < 20:
                reason = "short_prethrow_window"
            elif (live.time.diff().dt.total_seconds().dropna() > .21).any():
                reason = "frame_gap"
            elif not np.isfinite(live.s).all() or live.s.lt(0).any():
                reason = "invalid_speed"
            if reason:
                counts[reason] += 1
                rejected.append(dict(zip(KEYS, key), season=year, reason=reason))
                continue
            smooth = live.s.rolling(3, center=True, min_periods=1).median()
            dt = live.time.diff().dt.total_seconds().to_numpy()[1:]
            coordinate = np.linalg.norm(np.diff(live[["x", "y"]].to_numpy(), axis=0), axis=1) / dt
            mask = live.s.to_numpy()[1:] > 2
            if mask.any():
                coordinate_ratios.append(float(np.median(coordinate[mask] / live.s.to_numpy()[1:][mask])))
            all_output.append(dict(zip(KEYS, key), game_peak_speed=float(smooth.quantile(.95)),
                                   snap_speed=float(live.s.iloc[0]), window_duration=duration,
                                   frame_count=len(live)))
            counts["accepted"] += 1
        year_audits.append({"season": year, "scanned_rows": scanned, "selected_rows": len(selected),
                            "metadata_plays": len(year_meta), "tracked_plays": selected.groupby(KEYS).ngroups,
                            "counts": dict(counts), "events": dict(events),
                            "coordinate_to_s_ratio_median": float(np.median(coordinate_ratios))})
        print(f"{year}: {dict(counts)}", flush=True)
    result = pd.DataFrame(all_output).merge(metadata, on=KEYS, validate="one_to_one")
    assert len(result) + len(rejected) == len(metadata), "Every eligible play must be accounted for"
    result["window_duration_sq"] = result.window_duration ** 2
    result.to_csv(OUT / "rookie_wr_route_speed.csv", index=False)
    pd.DataFrame(rejected).to_csv(REPORT / "game_rejected.csv", index=False)
    report = {"combine": combine_qa, "game_years": year_audits,
              "accepted_game_plays": len(result), "accepted_game_players": result.nfl_id.nunique()}
    (REPORT / "extraction_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
