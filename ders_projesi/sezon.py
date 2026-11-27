"""Player-season features from regular-season game data (player_play + game tracking)."""
import numpy as np
import pandas as pd

from .veri import OUT, read

CACHE = OUT / "cache"
SEASONS = (2023, 2024, 2025)


def _bool(s):
    return s.astype(str).str.upper().map({"TRUE": 1.0, "FALSE": 0.0})


def play_season_stats():
    """One row per (nfl_id, season) from regular-season player_play rows."""
    cols = ["game_id", "play_id", "nfl_id", "team_abbr", "possession_team", "target",
            "rec_yards", "rush_yards", "route_ran", "pressure_allowed", "sack", "tackle"]
    pp = read("player_play.csv", usecols=cols, low_memory=False)
    g = read("games.csv")[["game_id", "season", "season_type"]]
    pp = pp.merge(g, on="game_id")
    pp = pp[pp["season_type"] == "REG"].copy()
    pp["off"] = (pp["team_abbr"] == pp["possession_team"]).astype(float)
    pp["target_b"] = _bool(pp["target"])
    pp["pressure_b"] = _bool(pp["pressure_allowed"])
    pp["route_b"] = pp["route_ran"].notna().astype(float)
    for c in ["rec_yards", "rush_yards", "sack", "tackle"]:
        pp[c] = pd.to_numeric(pp[c], errors="coerce")
    grp = pp.groupby(["nfl_id", "season"])
    out = grp.agg(snaps=("play_id", "size"), games=("game_id", "nunique"),
                  off_share=("off", "mean"), targets=("target_b", "sum"),
                  routes=("route_b", "sum"), rec_yards=("rec_yards", "sum"),
                  rush_yards=("rush_yards", "sum"), sacks=("sack", "sum"),
                  tackles=("tackle", "sum"), pressure_plays=("pressure_b", "count"),
                  pressures=("pressure_b", "sum")).reset_index()
    out["snaps_per_game"] = out["snaps"] / out["games"]
    out["pressure_rate"] = out["pressures"] / out["pressure_plays"].replace(0, np.nan)
    out["targets_per_route"] = out["targets"] / out["routes"].replace(0, np.nan)
    return out


def tracking_season_stats():
    """Mean of per-play peak speed / acceleration per (nfl_id, season), regular season. Cached."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "game_tracking_season.csv"
    if path.exists():
        return pd.read_csv(path)
    g = read("games.csv")[["game_id", "season", "season_type"]]
    reg = set(g.loc[g["season_type"] == "REG", "game_id"])
    parts = []
    for season in SEASONS:
        t = read(f"game_tracking_{season}.csv", usecols=["game_id", "play_id", "nfl_id", "s", "a"],
                 dtype={"s": "float32", "a": "float32"})
        t = t[t["game_id"].isin(reg)]
        per_play = t.groupby(["game_id", "play_id", "nfl_id"])[["s", "a"]].max().reset_index()
        agg = per_play.groupby("nfl_id").agg(trk_plays=("s", "size"), trk_peak_s=("s", "mean"),
                                             trk_peak_a=("a", "mean"),
                                             trk_top_s=("s", lambda x: np.percentile(x, 90)))
        agg["season"] = season
        parts.append(agg.reset_index())
        del t, per_play
    out = pd.concat(parts, ignore_index=True)
    out.to_csv(path, index=False)
    return out


ROOKIE_COLS = ["snaps", "games", "snaps_per_game", "off_share", "targets", "routes", "rec_yards",
               "rush_yards", "sacks", "tackles", "pressure_rate", "targets_per_route",
               "trk_plays", "trk_peak_s", "trk_peak_a", "trk_top_s"]


def season_table():
    return play_season_stats().merge(tracking_season_stats(), on=["nfl_id", "season"], how="outer")
