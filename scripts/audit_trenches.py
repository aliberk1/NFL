"""Assess trench-role coverage and measurement quality before association tests."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/nfl-big-data-bowl-2027"
OUT = ROOT / "reports/trenches"
DRILLS = ["RUN_THE_HOOP_DRILL", "PASS_RUSH_DRILL", "PASS_PRO-MIRROR_DRILL", "PASS_PRO_MIRROR_DRILL"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    players = pd.read_csv(DATA / "players.csv")
    games = pd.read_csv(DATA / "games.csv")
    pp = pd.read_csv(DATA / "player_play.csv", low_memory=False)
    pp = pp.merge(players[["nfl_id", "nfl_position", "draft_year"]], on="nfl_id", validate="many_to_one")
    pp = pp.merge(games[["game_id", "season", "season_type"]], on="game_id", validate="many_to_one")
    pp = pp.loc[pp.season_type.eq("REG") & pp.season.eq(pp.draft_year) & pp.play_nullified_by_penalty.eq("N")]
    groups = {"OL": ["T", "G", "C"], "DL": ["DE", "OLB", "DT", "NT"]}
    fields = ["pressure_allowed", "peak_pressure_probability_allowed", "time_to_pressure_allowed",
              "player_get_off", "time_to_pressure", "quick_pressure", "unblocked_pressure",
              "blitzing", "pass_rushers_encountered", "dropback_duration"]
    report = {}
    for name, positions in groups.items():
        subset = pp.loc[pp.nfl_position.isin(positions)].copy()
        details = {"players": subset.nfl_id.nunique(), "rows": len(subset),
                   "lineups": subset.lined_up_position.value_counts().to_dict(),
                   "coverage": {}, "numeric_distributions": {}}
        for field in fields:
            valid = subset.loc[subset[field].notna()]
            details["coverage"][field] = {"rows": len(valid), "players": valid.nfl_id.nunique(),
                "values": {str(k): int(v) for k, v in valid[field].value_counts().head(8).items()}}
            numeric = pd.to_numeric(valid[field], errors="coerce")
            details["numeric_distributions"][field] = numeric.describe(percentiles=[.01, .5, .99]).to_dict()
        outcome = "pressure_allowed" if name == "OL" else "player_get_off"
        valid = subset.loc[subset[outcome].notna()]
        count = valid.groupby(["nfl_id", "draft_year", "nfl_position"]).size().reset_index(name="plays")
        count.to_csv(OUT / f"{name.lower()}_rookie_coverage.csv", index=False)
        details["at_least_50_by_year_position"] = count.loc[count.plays.ge(50)].groupby([
            "draft_year", "nfl_position"]).size().rename("players").reset_index().to_dict("records")
        subset.to_csv(OUT / f"{name.lower()}_rookie_plays.csv", index=False)
        report[name] = details

    tracking = pd.read_csv(DATA / "combine_tracking.csv")
    tracking = tracking.loc[tracking.entity_type.eq("PLAYER") & tracking.drill_name.isin(DRILLS)].copy()
    tracking["time"] = pd.to_datetime(tracking.time)
    summaries = []
    for key, g in tracking.groupby(["nfl_id", "draft_year", "drill_name", "event_id", "attempt"]):
        g = g.sort_values("time")
        summaries.append(dict(zip(["nfl_id", "draft_year", "drill_name", "event_id", "attempt"], key),
                              frames=len(g), duration=(g.time.iloc[-1] - g.time.iloc[0]).total_seconds(),
                              max_speed=g.s.max(), x_start=g.x.iloc[0], y_start=g.y.iloc[0]))
    pd.DataFrame(summaries).to_csv(OUT / "drill_attempt_coverage.csv", index=False)
    for kind, drills in [("hoop", ["RUN_THE_HOOP_DRILL"]),
                         ("mirror", ["PASS_PRO-MIRROR_DRILL", "PASS_PRO_MIRROR_DRILL"])]:
        fig, axes = plt.subplots(3, 3, figsize=(11, 10))
        for row, year in enumerate((2023, 2024, 2025)):
            subset = tracking.loc[tracking.drill_name.isin(drills) & tracking.draft_year.eq(year)]
            for ax, (key, g) in zip(axes[row], list(subset.groupby(["nfl_id", "event_id", "attempt"]))[:3]):
                g = g.sort_values("time")
                ax.plot(g.x, g.y, alpha=.5)
                points = ax.scatter(g.x, g.y, c=g.s, cmap="viridis", s=12)
                ax.scatter(g.x.iloc[0], g.y.iloc[0], marker="x", color="red", s=65)
                ax.set_aspect("equal", adjustable="datalim")
                name = players.set_index("nfl_id").loc[key[0], "display_name"]
                ax.set_title(f"{year}: {name}", fontsize=10)
                fig.colorbar(points, ax=ax, label="Speed")
        fig.suptitle(f"{kind}: raw trajectories before outcome tests; red cross = start")
        fig.tight_layout()
        fig.savefig(OUT / f"{kind}_trajectory_audit.png", dpi=140)
        plt.close(fig)
    (OUT / "coverage_audit.json").write_text(json.dumps(report, indent=2, allow_nan=True), encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
