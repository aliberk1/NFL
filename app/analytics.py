import csv
import hashlib
import io
import json
from contextlib import contextmanager
from typing import Any

import duckdb

from app.config import DB, ROOT

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
    payload = result({
        "players": query("SELECT count(*) AS count, min(draft_year) AS first_draft, max(draft_year) AS last_draft FROM players"),
        "seasons": query("SELECT season, season_type, count(*) AS games FROM games GROUP BY season, season_type ORDER BY season, season_type"),
        "coverage": query("SELECT * FROM team_season_coverage ORDER BY season, team_abbr"),
    }, ["players", "games", "player_play"])
    catalog = DB.parent / "catalog.json"
    payload["provenance"] = None
    if catalog.exists():
        info = json.loads(catalog.read_text(encoding="utf-8"))
        payload["provenance"] = {
            key: info.get(key) for key in ("source", "loaded_at_utc", "data_version", "seasons")
        }
    return payload


def search_players(name):
    # Literal substring matching, with parameter binding.
    return result(query(
        "SELECT nfl_id, display_name, nfl_position, draft_year FROM players "
        "WHERE contains(lower(display_name), lower(?)) ORDER BY display_name LIMIT 25", [name]
    ), ["players"])


def player_directory():
    return result(query("""
        WITH teams AS (
            SELECT nfl_id, string_agg(DISTINCT team_abbr, ', ' ORDER BY team_abbr) AS teams
            FROM player_play GROUP BY nfl_id
        )
        SELECT p.nfl_id, p.display_name, p.nfl_position, p.draft_year,
               coalesce(t.teams, 'Takım kaydı yok') AS teams
        FROM players p LEFT JOIN teams t USING (nfl_id)
        ORDER BY p.display_name, p.nfl_id
    """), ["players", "player_play"])


def player_profile(player_id):
    return result({
        "player": query("SELECT * FROM players WHERE nfl_id = ?", [player_id]),
        "combine": query("SELECT * FROM combine_results WHERE nfl_id = ?", [player_id]),
        "career_snapshot": query("SELECT * FROM player_career_successes WHERE nfl_id = ?", [player_id]),
    }, ["players", "combine_results", "player_career_successes"])


def _read_verified_research_artifact(package: str, relative_path: str) -> tuple[bytes, str]:
    manifest_path = ROOT / package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"{manifest_path} geçerli bir araştırma manifesti değil.")
    verification = manifest.get("verification")
    if not isinstance(verification, dict) or verification.get("status") != "passed":
        raise ValueError(f"{manifest_path} doğrulamadan geçmemiş.")

    artifacts = manifest.get("files")
    if artifacts is None:
        artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError(f"{manifest_path} sürümlü dosya listesini içermiyor.")
    entry = next(
        (
            item for item in artifacts
            if isinstance(item, dict)
            and item.get("path", item.get("file")) == relative_path
        ),
        None,
    )
    if entry is None or not isinstance(entry.get("sha256"), str):
        raise ValueError(f"{relative_path} {manifest_path} içinde sürümlenmemiş.")

    artifact_path = (ROOT / relative_path).resolve()
    if not artifact_path.is_relative_to(ROOT.resolve()):
        raise ValueError(f"{relative_path} proje dizininin dışına çıkıyor.")
    content = artifact_path.read_bytes()
    hash_content = content
    if artifact_path.suffix.lower() in {".csv", ".html", ".json", ".md", ".txt"}:
        hash_content = content.replace(b"\r\n", b"\n")
    actual_digest = hashlib.sha256(hash_content).hexdigest()
    if actual_digest != entry["sha256"]:
        raise ValueError(f"{relative_path} manifestteki SHA-256 özetiyle eşleşmiyor.")
    return content, actual_digest


def _verified_research_json(package: str, relative_path: str) -> tuple[dict[str, Any], str]:
    content, digest = _read_verified_research_artifact(package, relative_path)
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError(f"{relative_path} bir JSON nesnesi olmalıdır.")
    return data, digest


def _verified_research_csv(package: str, relative_path: str) -> tuple[list[dict[str, str]], str]:
    content, digest = _read_verified_research_artifact(package, relative_path)
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    if reader.fieldnames is None:
        raise ValueError(f"{relative_path} CSV başlık satırı içermiyor.")
    return list(reader), digest


def research_snapshot() -> dict[str, Any]:
    ol_summary, ol_summary_digest = _verified_research_json(
        "submission_mirror", "reports/trenches/mirror_summary.json"
    )
    ol_measurements, ol_measurements_digest = _verified_research_json(
        "submission_mirror", "reports/trenches/mirror_measurement_summary.json"
    )
    ol_cohort, ol_cohort_digest = _verified_research_csv(
        "submission_mirror", "reports/trenches/mirror_measurement_rank_comparison.csv"
    )
    ol_explorer, ol_explorer_digest = _read_verified_research_artifact(
        "submission_mirror", "submission_mirror/mirror_explorer.html"
    )
    ol_chart, ol_chart_digest = _read_verified_research_artifact(
        "submission_mirror", "submission_mirror/figures/mirror_model_comparison.png"
    )
    wr_summary, wr_summary_digest = _verified_research_json(
        "submission", "reports/speed_study/summary.json"
    )
    wr_cohort, wr_cohort_digest = _verified_research_csv(
        "submission", "reports/speed_study/player_features.csv"
    )
    wr_chart, wr_chart_digest = _read_verified_research_artifact(
        "submission", "submission/figures/speed_transfer_results.png"
    )

    return {
        "ol": {
            "summary": ol_summary,
            "measurements": ol_measurements,
            "cohort": ol_cohort,
            "explorer_html": ol_explorer.decode("utf-8"),
            "model_chart": ol_chart,
            "digests": {
                "summary": ol_summary_digest,
                "measurements": ol_measurements_digest,
                "cohort": ol_cohort_digest,
                "explorer": ol_explorer_digest,
                "model_chart": ol_chart_digest,
            },
        },
        "wr": {
            "summary": wr_summary,
            "cohort": wr_cohort,
            "model_chart": wr_chart,
            "digests": {
                "summary": wr_summary_digest,
                "cohort": wr_cohort_digest,
                "model_chart": wr_chart_digest,
            },
        },
    }


def same_comparison_context(players: list[dict[str, Any]]) -> bool:
    if not players:
        return False
    contexts = set()
    for player in players:
        position = player.get("nfl_position")
        draft_year = player.get("draft_year")
        if position is None or draft_year is None:
            return False
        contexts.add((position, draft_year))
    return len(contexts) == 1


def player_performance(player_ids, season=None, season_type=None):
    if not player_ids or len(player_ids) > 10:
        raise ValueError("1–10 oyuncu kimliği gereklidir.")
    if season_type is not None and season_type not in ("PRE", "REG", "POST"):
        raise ValueError("season_type PRE, REG veya POST olmalıdır.")
    marks = ",".join("?" for _ in player_ids)
    params = list(player_ids)
    season_filter = ""
    if season is not None:
        season_filter = " AND g.season = ?"
        params.append(season)
    if season_type is not None:
        season_filter += " AND g.season_type = ?"
        params.append(season_type)
    rows = query(f"""
        SELECT p.nfl_id, p.display_name, p.nfl_position, g.season, g.season_type, pp.team_abbr,
               count(*) AS player_play_rows,
               count(DISTINCT pp.game_id) AS games,
               count(pp.pressure_allowed) AS pressure_labeled_plays,
               avg(CAST(pp.pressure_allowed AS INTEGER)) AS pressure_allowed_rate,
               sum(pp.rec_yards) AS receiving_yards,
               count(pp.rec_yards) AS receiving_labeled_plays,
               sum(pp.rush_yards) AS rushing_yards,
               count(pp.rush_yards) AS rushing_labeled_plays,
               sum(pp.sack) AS sacks,
               count(pp.sack) AS sack_labeled_plays,
               sum(pp.tackle) AS tackles,
               count(pp.tackle) AS tackle_labeled_plays,
               sum(pp.sack) / count(DISTINCT pp.game_id) AS sacks_per_observed_game
        FROM player_play pp JOIN players p USING (nfl_id) JOIN games g USING (game_id)
        WHERE pp.nfl_id IN ({marks}) {season_filter}
        GROUP BY p.nfl_id, p.display_name, p.nfl_position, g.season, g.season_type, pp.team_abbr
        ORDER BY g.season, g.season_type, p.display_name
    """, params)
    payload = result(rows, ["players", "games", "player_play"])
    payload["metric_definitions"] = {
        "games": "Oyuncunun seçilen sezon/tür/takım grubunda kaydının bulunduğu benzersiz game_id sayısı. Maç birimindedir; oyuncu–oyun satırı veya takımın tüm maç sayısı değildir.",
        "player_play_rows": "Oyuncu–oyun kayıt sayısı. Bir maçta birden çok kayıt bulunur. Maç sayısı değildir.",
        "sacks": "Datasetin sack alanındaki sayısal değerlerin toplamı; 0.5 gibi kesirli krediler korunur. Resmi istatistikle aynı olduğu varsayılmaz.",
        "sack_labeled_plays": "sack alanı dolu kayıtların sayısı. Toplam satırdan azsa sack ölçümünün kapsamı kısmi olabilir.",
        "tackles": "Datasetin tackle alanındaki sayısal değerlerin toplamı; yalnızca etiketli oyunları kapsar.",
        "tackle_labeled_plays": "tackle alanı dolu oyun sayısı; ölçüm kapsamını gösterir.",
        "sacks_per_observed_game": "Kodda hesaplanan sacks / games. Birimi gözlenen maç başına sack; pas baskısı fırsatı veya snap başına oran değildir.",
        "pressure_labeled_plays": "pressure_allowed alanı dolu kayıtların sayısı; pressure_allowed_rate paydasıdır.",
        "pressure_allowed_rate": "Etiketli kayıtlardaki baskı verme oranı (0–1). Savunmacının baskı üretme oranı değildir.",
        "receiving_yards": "Dolu rec_yards değerlerinin toplamı; tümü eksikse null.",
        "receiving_labeled_plays": "rec_yards alanı dolu oyun sayısı; pas yardı ölçümünün kapsamıdır.",
        "rushing_yards": "Dolu rush_yards değerlerinin toplamı; tümü eksikse null.",
        "rushing_labeled_plays": "rush_yards alanı dolu oyun sayısı; koşu yardı ölçümünün kapsamıdır.",
    }
    payload["interpretation_rules"] = [
        "PRE, REG ve POST gruplarını karıştırma. Farklı takımlardaki oranları basitçe ortalama.",
        "Tek metrik üstünlüğünü genel yetenek veya en güçlü/en iyi sezon olarak sunma.",
        "Maç başına sack artışı snap veya pass-rush fırsatı başına verim artışını kanıtlamaz.",
        "null eksiktir; sıfır değildir. Az gözlemde kesin üstünlük veya gelişim iddiası üretme.",
        "Pozisyonlar farklı fırsatlara sahiptir: pressure_allowed özellikle hücum hattı, rec_yards pas yakalayıcılar, rush_yards koşu rolleri, sack savunma rolleri için anlamlıdır. Etiket sayısı ve gözlenen maç sayısı azsa oranları karşılaştırma.",
    ]
    payload["scope"] = {"season": season, "season_type": season_type or "PRE/REG/POST ayrı gruplar"}
    return payload


def team_summary(team, season):
    return result(query(
        "SELECT * FROM team_season_coverage WHERE upper(team_abbr) = upper(?) AND season = ?",
        [team, season]), ["games", "player_play"])


def as_json(value):
    return json.dumps(value, ensure_ascii=False, default=str, allow_nan=False)
