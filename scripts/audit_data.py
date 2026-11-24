"""Summarize available players, Combine drills and regular-season outcomes."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "nfl-big-data-bowl-2027"


def rows(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as source:
        yield from csv.DictReader(source)


def present(value):
    return value not in (None, "", "NA")


def main():
    players = {r["nfl_id"]: r for r in rows("players.csv")}
    regular_games = {r["game_id"] for r in rows("games.csv") if r["season_type"] == "REG"}
    combine = list(rows("combine_results.csv"))
    drill_players = defaultdict(set)
    tracking_players = set()
    tracking_rows = 0
    for r in rows("combine_tracking.csv"):
        tracking_rows += 1
        if r["entity_type"] != "PLAYER":
            continue
        tracking_players.add(r["nfl_id"])
        drill_players[r["drill_name"]].add(r["nfl_id"])

    outcome_fields = ["separation_at_pass_forward", "route_ran", "yards_after_catch",
                      "player_get_off", "time_to_pressure", "pressure_allowed"]
    counts = defaultdict(Counter)
    outcome_players = defaultdict(set)
    game_players = set()
    for r in rows("player_play.csv"):
        if r["game_id"] not in regular_games:
            continue
        pid = r["nfl_id"]
        game_players.add(pid)
        position = players.get(pid, {}).get("nfl_position", "UNKNOWN")
        counts[position]["player_play_rows"] += 1
        for field in outcome_fields:
            if present(r[field]):
                counts[position][field] += 1
                outcome_players[(position, field)].add(pid)

    report = {
        "player_count": len(players),
        "positions": dict(Counter(p["nfl_position"] for p in players.values())),
        "draft_years": dict(Counter(p["draft_year"] for p in players.values())),
        "combine_result_rows": len(combine),
        "combine_results_nonmissing": {k: sum(present(r[k]) for r in combine) for k in combine[0]},
        "combine_tracking_rows": tracking_rows,
        "combine_tracking_players": len(tracking_players),
        "combine_and_regular_season_players_by_position": dict(Counter(
            players.get(pid, {}).get("nfl_position", "UNKNOWN")
            for pid in tracking_players & game_players)),
        "drills": {k: {"players": len(v), "positions": dict(Counter(
            players.get(pid, {}).get("nfl_position", "UNKNOWN") for pid in v))}
            for k, v in sorted(drill_players.items())},
        "regular_season_outcomes": {pos: {
            "nonmissing_rows": dict(c),
            "players_with_outcome": {field: len(outcome_players[(pos, field)]) for field in outcome_fields},
            "combine_players_with_outcome": {field: len(outcome_players[(pos, field)] & tracking_players)
                                             for field in outcome_fields},
        } for pos, c in sorted(counts.items())},
    }
    output = ROOT / "reports" / "data_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
