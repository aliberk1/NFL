"""Execute the standalone notebook from raw data and compare independent outputs."""
import json
import os
from pathlib import Path
import time

import nbformat
from nbclient import NotebookClient
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    verification = ROOT / "verification/notebook_run"
    verification.mkdir(parents=True, exist_ok=True)
    os.environ["NFL_DATA_DIR"] = str(ROOT / "data/nfl-big-data-bowl-2027")
    os.environ["NFL_WORK_DIR"] = str(verification)
    notebook_path = ROOT / "submission/receiver_speed_translation.ipynb"
    nb = nbformat.read(notebook_path, as_version=4)
    started = time.perf_counter()
    client = NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}})
    client.execute()
    nbformat.validate(nb)
    executed = ROOT / "submission/receiver_speed_translation.executed.ipynb"
    nbformat.write(nb, executed)
    checks = []
    for relative in ["data/processed/rookie_wr_route_speed.csv", "data/processed/combine_speed_players.csv",
                     "reports/speed_study/forward_year_scores.csv", "reports/speed_study/forward_year_predictions.csv",
                     "reports/speed_study/post_hoc_peak_only_ablation.csv",
                     "reports/speed_study/correlation_diagnostics.csv"]:
        expected = pd.read_csv(ROOT / relative)
        actual = pd.read_csv(verification / relative)
        pd.testing.assert_frame_equal(expected, actual, check_exact=False, rtol=1e-9, atol=1e-10)
        checks.append({"file": relative, "rows": len(actual), "match": True})
    audit = json.loads((verification / "reports/speed_study/extraction_audit.json").read_text())
    for year in audit["game_years"]:
        assert sum(year["counts"].values()) == year["metadata_plays"]
    errors = [output for cell in nb.cells if cell.cell_type == "code"
              for output in cell.get("outputs", []) if output.output_type == "error"]
    assert not errors
    result = {"status": "passed", "execution_seconds": round(time.perf_counter() - started, 2),
              "executed_code_cells": sum(cell.cell_type == "code" for cell in nb.cells),
              "comparison_checks": checks, "all_eligible_plays_accounted_for": True,
              "notebook_errors": len(errors), "executed_notebook": str(executed)}
    (ROOT / "verification/result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
