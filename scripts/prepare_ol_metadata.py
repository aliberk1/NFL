"""Build the required rookie OL metadata directly from competition inputs."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/nfl-big-data-bowl-2027"
OUT = ROOT / "reports/trenches"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    players = pd.read_csv(DATA / "players.csv")
    games = pd.read_csv(DATA / "games.csv")
    columns = ["game_id", "play_id", "nfl_id", "lined_up_position", "play_nullified_by_penalty",
               "pressure_allowed", "peak_pressure_probability_allowed", "time_to_pressure_allowed",
               "pass_rushers_encountered", "dropback_duration", "down", "yards_to_go",
               "offense_formation"]
    plays = pd.read_csv(DATA / "player_play.csv", usecols=columns)
    assert not plays.duplicated(["game_id", "play_id", "nfl_id"]).any()
    plays = plays.merge(players[["nfl_id", "nfl_position", "draft_year"]], on="nfl_id", validate="many_to_one")
    plays = plays.merge(games[["game_id", "season", "season_type"]], on="game_id", validate="many_to_one")
    plays = plays.loc[plays.nfl_position.isin(["T", "G", "C"]) & plays.season_type.eq("REG") &
                      plays.season.eq(plays.draft_year) & plays.play_nullified_by_penalty.eq("N")]
    plays.to_csv(OUT / "ol_rookie_plays.csv", index=False)
    print(f"Rookie OL metadata: {len(plays)} player-plays, {plays.nfl_id.nunique()} players")


if __name__ == "__main__":
    main()
