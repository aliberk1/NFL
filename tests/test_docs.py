"""Keep published documents consistent with the repository and recorded evidence."""
import csv
import json
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

from app.api import app

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
DOCUMENTS = [ROOT / "README.md", ROOT / "CHANGELOG.md", *sorted((ROOT / "docs").glob("*.md"))]


def turkish(value, digits):
    return f"{value:.{digits}f}".replace(".", ",")


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda path: path.name)
def test_relative_links_exist(path):
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if re.match(r"[a-z]+:|#", target):
            continue
        file = path.parent / unquote(target.split("#")[0])
        assert file.exists(), f"{path.name}: {target}"


def test_readme_ol_claims_match_recorded_results():
    measured = json.loads((ROOT / "reports/trenches/mirror_measurement_summary.json").read_text(encoding="utf-8"))
    summary = json.loads((ROOT / "reports/trenches/mirror_summary.json").read_text(encoding="utf-8"))
    drills = measured["ol_drill_suite"]
    assert all(drill["peak_in_exit_fraction"] == 1 for drill in drills)
    assert f"{sum(drill['accepted_attempts'] for drill in drills)} kaydın tamamında" in README
    assert f"**{measured['players']} oyuncu**" in README
    assert f"r = {measured['pooled_rank_correlation']:.3f}" in README
    assert f"{summary['players']} çaylak OL ve {summary['plays']:,}".replace(",", ".") in README
    scores = {row["model"]: row for row in summary["scores"]
              if row["variant"] == "primary_with_duration" and row["test_year"] == 2025}
    for model in ("mean_reference", "classic", "mirror_phase"):
        assert turkish(scores[model]["mae_pp"], 3) in README
    assert scores["mirror_phase"]["ci_low"] < 0 < scores["mirror_phase"]["ci_high"]


def test_readme_wr_claims_match_recorded_results():
    summary = json.loads((ROOT / "reports/speed_study/summary.json").read_text(encoding="utf-8"))
    assert f"{summary['primary_players']} çaylak WR ve {summary['primary_plays']:,}".replace(",", ".") in README
    assert all(row["ci_low"] < 0 < row["ci_high"] for row in summary["scores"])
    with (ROOT / "reports/speed_study/player_features.csv").open(encoding="utf-8-sig", newline="") as stream:
        assert len(list(csv.DictReader(stream))) >= summary["primary_players"]


def test_release_version_matches_application():
    version = re.search(r"^## v(\S+)", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.M).group(1)
    assert version == app.version
