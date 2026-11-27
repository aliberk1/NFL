"""Load competition data and build player-level targets.

Only the NFL Big Data Bowl 2027 competition files are used.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "nfl-big-data-bowl-2027"
OUT = ROOT / "nfl" / "ciktilar"

# Career data runs through the end of the 2025 season.
LAST_SEASON = 2025
GAMES_PER_SEASON = 17
UNDRAFTED_PICK = 262  # one past the last pick of a 7-round draft

POSITION_GROUP = {
    "C": "OL", "G": "OL", "T": "OL",
    "DE": "DL", "DT": "DL", "NT": "DL",
    "OLB": "LB", "ILB": "LB", "MLB": "LB",
    "CB": "DB", "FS": "DB", "SS": "DB", "DB": "DB",
    "WR": "WR", "TE": "TE",
    "RB": "OTHER", "FB": "OTHER",
}

COMBINE_MEASURES = [
    "combine_height", "combine_weight", "hand_size", "arm_length", "wing_span",
    "ten_yd_split", "forty", "vertical", "broad_jump", "three_cone",
    "short_shuttle", "bench_reps",
]


def read(name, **kw):
    return pd.read_csv(DATA / name, **kw)


def load_players(starter_threshold=0.5):
    """One row per player with pre-draft information and career targets."""
    players = read("players.csv")
    career = read("player_career_successes.csv")
    combine = read("combine_results.csv").drop(columns=["draft_year"])
    df = players.merge(career, on="nfl_id").merge(combine, on="nfl_id", how="left")

    df["position_group"] = df["nfl_position"].map(POSITION_GROUP).fillna("OTHER")
    df["seasons_available"] = LAST_SEASON - df["draft_year"] + 1
    df["start_rate"] = (
        df["career_games_started"] / (GAMES_PER_SEASON * df["seasons_available"])
    ).clip(upper=1.0)
    df["active_rate"] = (
        df["career_games_active"] / (GAMES_PER_SEASON * df["seasons_available"])
    ).clip(upper=1.0)
    df["y_starter"] = (df["start_rate"] >= starter_threshold).astype(int)
    df["y_honors"] = (
        df[["ap_all_pro_1st_team", "ap_all_pro_2nd_team", "pro_bowl_original_ballot"]]
        .sum(axis=1) > 0
    ).astype(int)

    # Sensitivity targets (choice C): other thresholds and a position-adjusted label.
    df["y_starter_40"] = (df["start_rate"] >= 0.4).astype(int)
    df["y_starter_60"] = (df["start_rate"] >= 0.6).astype(int)
    snaps = (df["career_offensive_snaps"] + df["career_defensive_snaps"]) / df["seasons_available"]
    df["snaps_per_season"] = snaps
    pct = snaps.groupby([df["position_group"], df["draft_year"]]).rank(pct=True, method="max")
    # OTHER (1 RB + 1 FB) cannot be ranked within its own group, so it is never positive.
    df["y_pos_top20"] = ((pct > 0.8) & (snaps > 0) & (df["position_group"] != "OTHER")).astype(int)

    df["undrafted"] = df["draft_overall_pick"].isna().astype(int)
    df["pick_filled"] = df["draft_overall_pick"].fillna(UNDRAFTED_PICK)
    df["log_pick"] = np.log(df["pick_filled"])
    df["round_filled"] = df["draft_round"].fillna(8)

    draft_day = pd.to_datetime(df["draft_year"].astype(str) + "-04-27")
    df["age_at_draft"] = (draft_day - pd.to_datetime(df["birth_date"])).dt.days / 365.25
    # Body-size ratios commonly used by scouts.
    df["bmi"] = 703 * df["combine_weight"] / df["combine_height"] ** 2
    df["speed_score"] = df["combine_weight"] * 200 / df["forty"] ** 4
    return df.sort_values("nfl_id").reset_index(drop=True)
