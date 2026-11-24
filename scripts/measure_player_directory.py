"""Compare the former full-directory load with the filtered, paged query path."""
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import duckdb
from app import analytics


def measure(call, runs=7):
    samples = []
    for _ in range(runs):
        analytics._cached_query.cache_clear()
        started = time.perf_counter()
        count = call()
        samples.append((time.perf_counter() - started) * 1000)
    return round(statistics.median(samples), 2), count


def measure_warm(call, runs=7):
    analytics._cached_query.cache_clear()
    call()  # Populate the cache before timing repeated unchanged queries.
    samples = []
    for _ in range(runs):
        started = time.perf_counter()
        call()
        samples.append((time.perf_counter() - started) * 1000)
    return round(statistics.median(samples), 2)


def main():
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "synthetic.duckdb"
        with duckdb.connect(str(database)) as con:
            con.execute("CREATE TABLE players AS SELECT i AS nfl_id, 'Player ' || lpad(i::VARCHAR, 5, '0') AS display_name, 'WR' AS nfl_position, 2023 AS draft_year FROM range(10000) r(i)")
            con.execute("CREATE TABLE player_play AS SELECT i AS nfl_id, 'MIN' AS team_abbr FROM range(10000) r(i)")
        analytics.DB = database

        def legacy_full_load():
            rows = analytics.query("""
                WITH teams AS (
                    SELECT nfl_id, string_agg(DISTINCT team_abbr, ', ' ORDER BY team_abbr) AS teams
                    FROM player_play GROUP BY nfl_id
                )
                SELECT p.nfl_id, p.display_name, p.nfl_position, p.draft_year,
                       coalesce(t.teams, 'Takım kaydı yok') AS teams
                FROM players p LEFT JOIN teams t USING (nfl_id)
                ORDER BY p.display_name, p.nfl_id
            """)
            matches = [row for row in rows if "Player 099" in row["display_name"]]
            return len(rows), len(matches)

        before_ms, before_counts = measure(legacy_full_load)

        def paged_search():
            result = analytics.player_directory(search="Player 099", limit=100)
            return result["data"]["total"], len(result["data"]["rows"])

        after_ms, after_counts = measure(paged_search)
        warm_ms = measure_warm(paged_search)
        print("Synthetic players: 10000; search: 'Player 099'; median of 7 cold runs")
        print(f"Before: {before_ms} ms, loaded {before_counts[0]} rows, displayed {before_counts[1]}")
        print(f"After:  {after_ms} ms, matched {after_counts[0]} rows, loaded {after_counts[1]}")
        print(f"Warm cache: {warm_ms} ms for the same filtered page")


if __name__ == "__main__":
    main()
