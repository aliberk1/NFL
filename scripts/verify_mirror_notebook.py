"""Independently rerun the complete mirror notebook from raw competition files."""
import base64
import contextlib
import io
import json
import os
from pathlib import Path
import time

import nbformat
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def execute_notebook_inprocess(nb):
    """Execute all code cells in an isolated namespace when ZMQ loopback sockets are unavailable."""
    import IPython.display as ipd
    from IPython.display import Image, Markdown
    ns = {"__name__": "__main__"}
    exec_count = 0
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        exec_count += 1
        cell.execution_count = exec_count
        cell.outputs = []
        buf = io.StringIO()

        def custom_display(*objs):
            for obj in objs:
                if isinstance(obj, Image) and getattr(obj, "filename", None):
                    b64 = base64.b64encode(Path(obj.filename).read_bytes()).decode("ascii")
                    cell.outputs.append(nbformat.v4.new_output(
                        "display_data", data={"image/png": b64, "text/plain": "<IPython.core.display.Image object>"}
                    ))
                elif isinstance(obj, pd.DataFrame):
                    cell.outputs.append(nbformat.v4.new_output(
                        "display_data", data={"text/plain": obj.to_string(), "text/html": obj.to_html()}
                    ))
                elif isinstance(obj, Markdown):
                    cell.outputs.append(nbformat.v4.new_output(
                        "display_data", data={"text/markdown": obj.data, "text/plain": obj.data}
                    ))
                else:
                    cell.outputs.append(nbformat.v4.new_output(
                        "display_data", data={"text/plain": repr(obj)}
                    ))

        ipd.display = custom_display
        ns["display"] = custom_display
        with contextlib.redirect_stdout(buf):
            exec(compile(cell.source, f"<cell-{exec_count}>", "exec"), ns)
        ns["display"] = custom_display
        text = buf.getvalue()
        if text:
            cell.outputs.insert(0, nbformat.v4.new_output("stream", name="stdout", text=text))


def main():
    work = ROOT / "verification/mirror_notebook_run"
    work.mkdir(parents=True, exist_ok=True)
    os.environ["NFL_DATA_DIR"] = str(ROOT / "data/nfl-big-data-bowl-2027")
    os.environ["NFL_WORK_DIR"] = str(work)
    nb = nbformat.read(ROOT / "submission_mirror/mirror_phase_validation.ipynb", as_version=4)
    start = time.perf_counter()
    execute_notebook_inprocess(nb)
    nbformat.validate(nb)
    nbformat.write(nb, ROOT / "submission_mirror/mirror_phase_validation.executed.ipynb")
    checks = []
    for filename in ["mirror_attempt_features.csv", "mirror_forward_year_scores.csv", "mirror_predictions.csv",
                     "movement_forward_year_scores.csv", "movement_predictions.csv", "mirror_measurement_rank_comparison.csv",
                     "mirror_full_refit_bootstrap.csv", "ol_drill_suite_audit.csv"]:
        expected = pd.read_csv(ROOT / "reports/trenches" / filename)
        actual = pd.read_csv(work / "reports/trenches" / filename)
        pd.testing.assert_frame_equal(expected, actual, check_exact=False, rtol=1e-8, atol=1e-9)
        checks.append({"file": filename, "rows": len(actual), "match": True})
    audit = json.loads((work / "reports/trenches/ol_movement_extraction_audit.json").read_text())
    assert all(sum(row["counts"].values()) == row["metadata_plays"] for row in audit["years"])
    errors = [out for cell in nb.cells if cell.cell_type == "code" for out in cell.get("outputs", []) if out.output_type == "error"]
    assert not errors
    result = {"status": "passed", "execution_seconds": round(time.perf_counter() - start, 2),
              "code_cells": sum(cell.cell_type == "code" for cell in nb.cells), "notebook_errors": len(errors),
              "comparison_checks": checks, "all_movement_opportunities_accounted_for": True}
    (ROOT / "verification/mirror_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
