"""Build a small, deterministic and entirely fictional demo database.

No value is sampled from or fitted to NFL or competition data. Run with
``python -m pipelines.demo_data``; an existing non-demo database is never replaced.
"""
import csv
import json
import random
import tempfile
from pathlib import Path

from pipelines import ingest

VERSION = 1
SOURCE = f"SENTETİK DEMO v{VERSION} — kurgusal kayıtlar, gerçek NFL verisi değildir"
TEAMS = ("DEMO-A", "DEMO-B", "DEMO-C", "DEMO-D")
POSITIONS = ("C", "G", "T", "WR", "TE", "RB", "DE", "CB")


def rows():
    rng = random.Random(20270101)
    players, combine, career, plays, roster = [], [], [], [], []
    schedule = [(season, kind) for season in (2024, 2025)
                for kind, count in (("PRE", 1), ("REG", 6), ("POST", 1)) for _ in range(count)]
    games = [{"game_id": 900000 + index, "season": season, "season_type": kind}
             for index, (season, kind) in enumerate(schedule)]
    for index in range(48):
        player_id, position = 900001 + index, POSITIONS[index % len(POSITIONS)]
        year = 2023 + (index // 8) % 3
        players.append({
            "nfl_id": player_id, "display_name": f"Kurgusal Oyuncu {index + 1:02d}",
            "nfl_position": position, "draft_year": year, "college_name": "Demo Üniversitesi",
            "college_conference": "Demo Konferansı", "draft_round": 1 + index % 7,
            "draft_overall_pick": index + 1,
        })
        # Some players deliberately lack measurements so missing-data states can be seen.
        if index % 12 != 11:
            combine.append({
                "nfl_id": player_id, "draft_year": year, "combine_position": position,
                "combine_height": rng.randint(70, 79), "combine_weight": rng.randint(190, 330),
                "forty": "NA" if index % 9 == 8 else round(rng.uniform(4.4, 5.4), 2),
                "vertical": round(rng.uniform(24, 40), 1), "broad_jump": rng.randint(95, 130),
                "short_shuttle": round(rng.uniform(4.1, 4.9), 2),
            })
        career.append({"nfl_id": player_id, "career_games_active": rng.randint(4, 32),
                       "career_games_started": rng.randint(0, 4)})
        roster.append((player_id, position, TEAMS[(index // 8) % 4]))
    for game in games:
        for player_id, position, team in roster:
            if rng.random() < 0.2:
                continue
            # One fictional player changes team between seasons.
            if player_id == 900001 and game["season"] == 2025:
                team = "DEMO-B"
            for play in range(1, 9):
                plays.append({
                    "game_id": game["game_id"], "play_id": play, "nfl_id": player_id, "team_abbr": team,
                    "pressure_allowed": str(rng.random() < 0.08).lower() if position in "CGT" else "NA",
                    "rec_yards": rng.choice((0, 0, 0, 4, 9, 15)) if position in ("WR", "TE") else "NA",
                    "rush_yards": rng.randint(-2, 12) if position == "RB" else "NA",
                    "sack": rng.choice((0.0,) * 18 + (0.5, 1.0)) if position == "DE" else "NA",
                    "tackle": rng.choice((0, 0, 0, 1)) if position in ("DE", "CB") else "NA",
                })
    return {"players": players, "games": games, "combine_results": combine,
            "player_career_successes": career, "player_play": plays}


def ensure():
    catalog = ingest.DB.parent / "catalog.json"
    if ingest.DB.exists():
        info = json.loads(catalog.read_text(encoding="utf-8")) if catalog.exists() else {}
        if not info.get("demo"):
            raise SystemExit(f"{ingest.DB} demo veritabanı değil; üzerine yazılmadı.")
        if info.get("source") == SOURCE:
            print(f"Demo ready: {ingest.DB}", flush=True)
            return
    with tempfile.TemporaryDirectory() as folder:
        for table, records in rows().items():
            with (Path(folder) / f"{table}.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(records[0]), lineterminator="\n")
                writer.writeheader()
                writer.writerows(records)
        ingest.build(data=Path(folder), source_name=SOURCE, demo=True)


if __name__ == "__main__":
    ensure()
