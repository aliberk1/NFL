"""Run with python -m pipelines.ingest. Tracking is not loaded in this MVP."""
import json
import os

import duckdb

from app.config import DATA, DB

TABLES = ["players", "games", "combine_results", "player_career_successes", "player_play"]


def build():
    DB.parent.mkdir(parents=True, exist_ok=True)
    staging = DB.with_suffix(".building.duckdb")
    if staging.exists():
        staging.unlink()
    con = duckdb.connect(str(staging))
    try:
        for table in TABLES:
            source = str(DATA / f"{table}.csv").replace("'", "''")
            con.execute(
                f"CREATE TABLE {table} AS SELECT * FROM read_csv_auto('{source}', "
                "header=true, nullstr='NA', sample_size=-1)"
            )
            print(f"{table}: {con.execute(f'SELECT count(*) FROM {table}').fetchone()[0]:,}", flush=True)
        for table, keys in [("players", "nfl_id"), ("games", "game_id"),
                            ("combine_results", "nfl_id, draft_year"),
                            ("player_play", "game_id, play_id, nfl_id")]:
            duplicate = con.execute(
                f"SELECT count(*) FROM (SELECT {keys} FROM {table} GROUP BY {keys} HAVING count(*) > 1)"
            ).fetchone()[0]
            if duplicate:
                raise ValueError(f"{table}: {duplicate} duplicate key groups")
        for table, key, parent in [("player_play", "nfl_id", "players"),
                                    ("player_play", "game_id", "games")]:
            missing = con.execute(
                f"SELECT count(*) FROM {table} c LEFT JOIN {parent} p USING ({key}) WHERE p.{key} IS NULL"
            ).fetchone()[0]
            if missing:
                raise ValueError(f"{table}: {missing} unmatched {key}")
        # A team/season view is descriptive of represented players, not the complete roster.
        con.execute("""
            CREATE VIEW team_season_coverage AS
            SELECT pp.team_abbr, g.season, count(DISTINCT pp.nfl_id) AS represented_players,
                   count(DISTINCT pp.game_id) AS represented_games,
                   count(DISTINCT (pp.game_id, pp.play_id)) AS represented_plays,
                   count(*) AS player_play_rows
            FROM player_play pp JOIN games g USING (game_id)
            GROUP BY pp.team_abbr, g.season
        """)
        catalog = {}
        for table in TABLES:
            catalog[table] = {
                "rows": con.execute(f"SELECT count(*) FROM {table}").fetchone()[0],
                "columns": [{"name": r[0], "type": r[1]} for r in con.execute(f"DESCRIBE {table}").fetchall()],
            }
        con.close()
        os.replace(staging, DB)
        (DB.parent / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
        print(f"Ready: {DB}", flush=True)
    except Exception:
        con.close()
        raise


if __name__ == "__main__":
    build()
