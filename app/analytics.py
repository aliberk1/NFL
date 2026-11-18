import json
from contextlib import contextmanager

import duckdb

from app.config import DB

COVERAGE_NOTE = (
    "Sonuçlar yalnızca dataset içindeki oyuncu ve oyun kayıtlarını kapsar; "
    "tam takım kadrosu veya bütün maç performansı olarak yorumlanmamalıdır. "
    "Tracking dosyaları bu sürümün sorgu katmanına henüz dahil değildir."
)


@contextmanager
def connection():
    if not DB.exists():
        raise FileNotFoundError("Veritabanı hazır değil. python -m pipelines.ingest çalıştırın.")
    con = duckdb.connect(str(DB), read_only=True)
    try:
        yield con
    finally:
        con.close()


def query(sql, params=None):
    with connection() as con:
        cursor = con.execute(sql, params or [])
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def result(data, sources):
    return {"data": data, "sources": sources, "coverage_notes": [COVERAGE_NOTE],
            "kind": "observed", "model_version": None}


def dataset_summary():
    return result({
        "players": query("SELECT count(*) AS count, min(draft_year) AS first_draft, max(draft_year) AS last_draft FROM players"),
        "seasons": query("SELECT season, season_type, count(*) AS games FROM games GROUP BY season, season_type ORDER BY season, season_type"),
        "coverage": query("SELECT * FROM team_season_coverage ORDER BY season, team_abbr"),
    }, ["players", "games", "player_play"])


def search_players(name):
    # Literal substring matching, with parameter binding.
    return result(query(
        "SELECT nfl_id, display_name, nfl_position, draft_year FROM players "
        "WHERE contains(lower(display_name), lower(?)) ORDER BY display_name LIMIT 25", [name]
    ), ["players"])


def player_profile(player_id):
    return result({
        "player": query("SELECT * FROM players WHERE nfl_id = ?", [player_id]),
        "combine": query("SELECT * FROM combine_results WHERE nfl_id = ?", [player_id]),
        "career_snapshot": query("SELECT * FROM player_career_successes WHERE nfl_id = ?", [player_id]),
    }, ["players", "combine_results", "player_career_successes"])


def player_performance(player_ids, season=None):
    if not player_ids or len(player_ids) > 10:
        raise ValueError("1–10 oyuncu kimliği gereklidir.")
    marks = ",".join("?" for _ in player_ids)
    params = list(player_ids)
    season_filter = ""
    if season is not None:
        season_filter = " AND g.season = ?"
        params.append(season)
    rows = query(f"""
        SELECT p.nfl_id, p.display_name, p.nfl_position, g.season, g.season_type, pp.team_abbr,
               count(*) AS player_play_rows,
               count(DISTINCT pp.game_id) AS games,
               count(pp.pressure_allowed) AS pressure_labeled_plays,
               avg(CAST(pp.pressure_allowed AS INTEGER)) AS pressure_allowed_rate,
               sum(pp.rec_yards) AS receiving_yards,
               sum(pp.rush_yards) AS rushing_yards,
               sum(CAST(pp.sack AS INTEGER)) AS sacks
        FROM player_play pp JOIN players p USING (nfl_id) JOIN games g USING (game_id)
        WHERE pp.nfl_id IN ({marks}) {season_filter}
        GROUP BY p.nfl_id, p.display_name, p.nfl_position, g.season, g.season_type, pp.team_abbr
        ORDER BY g.season, g.season_type, p.display_name
    """, params)
    return result(rows, ["players", "games", "player_play"])


def team_summary(team, season):
    return result(query(
        "SELECT * FROM team_season_coverage WHERE upper(team_abbr) = upper(?) AND season = ?",
        [team, season]), ["games", "player_play"])


def as_json(value):
    return json.dumps(value, ensure_ascii=False, default=str, allow_nan=False)
