"""Validate application CSVs and build the DuckDB snapshot."""

import hashlib
import json
import os
from datetime import datetime, timezone

import duckdb

from app.config import DATA, DB


# Columns used by the application are mandatory; other source columns are kept.
SCHEMA = {
    "players": {"nfl_id": "BIGINT", "display_name": "VARCHAR", "nfl_position": "VARCHAR", "draft_year": "BIGINT"},
    "games": {"game_id": "BIGINT", "season": "BIGINT", "season_type": "VARCHAR"},
    "combine_results": {"nfl_id": "BIGINT", "draft_year": "BIGINT"},
    "player_career_successes": {"nfl_id": "BIGINT"},
    "player_play": {
        "game_id": "BIGINT", "play_id": "BIGINT", "nfl_id": "BIGINT", "team_abbr": "VARCHAR",
        "pressure_allowed": "BOOLEAN", "rec_yards": "BIGINT", "rush_yards": "BIGINT", "sack": "DOUBLE",
    },
}
KEYS = {
    "players": ("nfl_id",), "games": ("game_id",),
    "combine_results": ("nfl_id", "draft_year"),
    "player_career_successes": ("nfl_id",),
    "player_play": ("game_id", "play_id", "nfl_id"),
}
REQUIRED_VALUES = {
    "players": ("nfl_id", "display_name"),
    "games": ("game_id", "season", "season_type"),
    "combine_results": ("nfl_id", "draft_year"),
    "player_career_successes": ("nfl_id",),
    "player_play": ("game_id", "play_id", "nfl_id", "team_abbr"),
}
FOREIGN_KEYS = (
    ("player_play", "nfl_id", "players"),
    ("player_play", "game_id", "games"),
    ("combine_results", "nfl_id", "players"),
    ("player_career_successes", "nfl_id", "players"),
)


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_table(con, table, report, errors):
    columns = {row[0]: row[1] for row in con.execute(f"DESCRIBE {table}").fetchall()}
    expected = SCHEMA[table]
    absent = sorted(set(expected) - set(columns))
    # A numeric column containing only whole numbers can be inferred as BIGINT.
    def compatible(actual, kind):
        return actual == kind or (kind == "DOUBLE" and
                                  (actual in ("BIGINT", "INTEGER") or actual.startswith("DECIMAL(")))

    wrong_types = {name: {"expected": kind, "actual": columns[name]}
                   for name, kind in expected.items() if name in columns and not compatible(columns[name], kind)}
    expressions = []
    for name, kind in columns.items():
        condition = f'"{name}" IS NULL'
        if kind == "VARCHAR":
            condition += f' OR trim("{name}") = \'\''
        expressions.append(f'count(*) FILTER (WHERE {condition}) AS "{name}"')
    missing = dict(zip(columns, con.execute(
        f"SELECT {', '.join(expressions)} FROM {table}").fetchone()))
    report["tables"][table] = {
        "rows": con.execute(f"SELECT count(*) FROM {table}").fetchone()[0],
        "columns": [{"name": name, "type": kind} for name, kind in columns.items()],
        "missing_values": missing,
        "missing_required_columns": absent,
        "wrong_types": wrong_types,
    }
    if absent:
        errors.append(f"{table}: eksik kolonlar: {', '.join(absent)}")
    if wrong_types:
        errors.append(f"{table}: yanlış veri tipleri: {', '.join(wrong_types)}")
    for name in REQUIRED_VALUES[table]:
        if name in missing and missing[name]:
            errors.append(f"{table}.{name}: {missing[name]} boş değer")
    if all(name in columns for name in KEYS[table]):
        keys = ", ".join(f'"{name}"' for name in KEYS[table])
        duplicates = con.execute(
            f"SELECT count(*) FROM (SELECT {keys} FROM {table} GROUP BY {keys} HAVING count(*) > 1)"
        ).fetchone()[0]
        report["tables"][table]["duplicate_key_groups"] = duplicates
        if duplicates:
            errors.append(f"{table}: {duplicates} tekrar anahtar grubu")


def build(data=None, source_name="NFL Big Data Bowl 2027 local CSV", demo=False):
    data = data or DATA
    DB.parent.mkdir(parents=True, exist_ok=True)
    staging = DB.with_suffix(".building.duckdb")
    if staging.exists():
        staging.unlink()
    report = {"source": source_name, "demo": demo,
              "loaded_at_utc": datetime.now(timezone.utc).isoformat(),
              "tables": {}, "foreign_keys": {}, "errors": []}
    errors = report["errors"]
    con = duckdb.connect(str(staging))
    try:
        sources = {}
        for table in SCHEMA:
            path = data / f"{table}.csv"
            if not path.is_file():
                errors.append(f"Eksik kaynak: {path}")
                continue
            sources[table] = {"file": path.name, "bytes": path.stat().st_size, "sha256": file_hash(path)}
            source = str(path).replace("'", "''")
            try:
                con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv_auto('{source}', "
                            "header=true, nullstr='NA', sample_size=-1)")
                validate_table(con, table, report, errors)
            except duckdb.Error as exc:
                errors.append(f"{table}: CSV okunamadı: {exc}")
        report["sources"] = sources
        report["data_version"] = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
        if not errors:
            for table, key, parent in FOREIGN_KEYS:
                missing = con.execute(
                    f"SELECT count(*) FROM {table} c LEFT JOIN {parent} p USING ({key}) WHERE p.{key} IS NULL"
                ).fetchone()[0]
                report["foreign_keys"][f"{table}.{key} -> {parent}.{key}"] = missing
                if missing:
                    errors.append(f"{table}: {missing} eşleşmeyen {key}")
        if not errors:
            con.execute("""
                CREATE VIEW team_season_coverage AS
                SELECT pp.team_abbr, g.season, count(DISTINCT pp.nfl_id) AS represented_players,
                       count(DISTINCT pp.game_id) AS represented_games,
                       count(DISTINCT (pp.game_id, pp.play_id)) AS represented_plays,
                       count(*) AS player_play_rows
                FROM player_play pp JOIN games g USING (game_id)
                GROUP BY pp.team_abbr, g.season
            """)
            report["seasons"] = [r[0] for r in con.execute("SELECT DISTINCT season FROM games ORDER BY season").fetchall()]
        report["status"] = "failed" if errors else "passed"
        (DB.parent / "quality_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        if errors:
            raise ValueError("Veri doğrulaması başarısız: " + "; ".join(errors))
        con.close()
        os.replace(staging, DB)
        (DB.parent / "catalog.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Ready: {DB} (version {report['data_version'][:12]})", flush=True)
    except Exception:
        con.close()
        if staging.exists():
            staging.unlink()
        raise


if __name__ == "__main__":
    build()
