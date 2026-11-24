"""Fixed 1.5-second early pass-protection movement for the mirror study cohort."""
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/nfl-big-data-bowl-2027"
OUT = ROOT / "reports/trenches"
KEYS = ["game_id", "play_id", "nfl_id"]
END_EVENTS = ["pass_forward", "tackle", "out_of_bounds", "qb_sack", "qb_strip_sack",
              "touchdown", "pass_outcome_incomplete", "fumble"]


def main():
    table = pd.read_csv(OUT / "mirror_model_players.csv")
    metadata = pd.read_csv(OUT / "ol_rookie_plays.csv", low_memory=False)
    metadata = metadata.loc[metadata.nfl_id.isin(table.nfl_id) & metadata.lined_up_position.isin(["T", "G", "C"]) &
                            metadata.pressure_allowed.notna() & metadata.pass_rushers_encountered.eq(1)].copy()
    assert not metadata.duplicated(KEYS).any()
    outputs, exclusions, audits = [], [], []
    for year in (2023, 2024, 2025):
        year_meta = metadata.loc[metadata.draft_year.eq(year)]
        year_ids = set(year_meta.nfl_id)
        year_games = set(year_meta.game_id)
        wanted = pd.MultiIndex.from_frame(year_meta[KEYS])
        frames = []
        for chunk in pd.read_csv(DATA / f"game_tracking_{year}.csv", chunksize=500000,
                                 usecols=KEYS + ["time", "x", "y", "s", "event"]):
            chunk = chunk.loc[chunk.nfl_id.isin(year_ids) & chunk.game_id.isin(year_games)]
            if len(chunk):
                chunk = chunk.loc[pd.MultiIndex.from_frame(chunk[KEYS]).isin(wanted)]
                if len(chunk):
                    frames.append(chunk)
        tracking = pd.concat(frames, ignore_index=True)
        tracking["time"] = pd.to_datetime(tracking.time)
        tracked = pd.MultiIndex.from_frame(tracking[KEYS].drop_duplicates())
        missing = year_meta.loc[~pd.MultiIndex.from_frame(year_meta[KEYS]).isin(tracked)]
        counts = Counter(missing_tracking=len(missing))
        exclusions.extend([{**row, "reason": "missing_tracking"} for row in missing[KEYS].to_dict("records")])
        for key, g in tracking.groupby(KEYS, sort=False):
            g = g.sort_values("time")
            snap = g.loc[g.event.eq("ball_snap"), "time"]
            reason = None
            if len(snap) != 1:
                reason = "missing_or_multiple_snap"
            elif g.time.duplicated().any():
                reason = "duplicate_time"
            if not reason:
                start, end = snap.iloc[0], snap.iloc[0] + pd.Timedelta(seconds=1.5)
                window = g.loc[g.time.ge(start) & g.time.le(end)]
                if (g.event.isin(END_EVENTS) & g.time.ge(start) & g.time.lt(end)).any():
                    reason = "early_throw_or_end"
                elif len(window) < 16 or window.time.iloc[-1] != end:
                    reason = "incomplete_window"
                elif (window.time.diff().dt.total_seconds().dropna() > .21).any():
                    reason = "frame_gap"
                elif not np.isfinite(window[["x", "y", "s"]].to_numpy()).all():
                    reason = "nonfinite_values"
            if reason:
                exclusions.append({**dict(zip(KEYS, key)), "reason": reason})
                counts[reason] += 1
                continue
            time = (window.time - start).dt.total_seconds().to_numpy()
            y = savgol_filter(window.y.to_numpy(), 5, 2)
            vy = np.gradient(y, time)
            outputs.append({**dict(zip(KEYS, key)), "game_lateral_speed_p75": float(np.quantile(np.abs(vy), .75)),
                            "snap_speed": float(window.s.iloc[0]), "frames": len(window)})
            counts["accepted"] += 1
        audits.append({"year": year, "metadata_plays": len(year_meta), "counts": dict(counts)})
        assert sum(counts.values()) == len(year_meta)
        print(f"{year}: {dict(counts)}", flush=True)
    result = pd.DataFrame(outputs).merge(metadata, on=KEYS, validate="one_to_one")
    result.to_csv(OUT / "ol_early_movement.csv", index=False)
    pd.DataFrame(exclusions).to_csv(OUT / "ol_early_movement_exclusions.csv", index=False)
    audit = {"years": audits, "accepted_plays": len(result), "accepted_players": result.nfl_id.nunique()}
    (OUT / "ol_movement_extraction_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
