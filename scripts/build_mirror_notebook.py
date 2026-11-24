"""Standalone flagship research notebook for Offensive Line Combine phase validation."""
from pathlib import Path
import nbformat

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
    text = text.replace('ROOT = Path(__file__).resolve().parents[1]', 'ROOT = WORK_DIR')
    text = text.replace('DATA = ROOT / "data/nfl-big-data-bowl-2027"', 'DATA = DATA_DIR')
    text = "\n".join(line for line in text.splitlines()
                     if not line.startswith("from analyze_mirror_protection import ")
                     and not line.startswith("from extract_mirror_features import "))
    return text.replace('if __name__ == "__main__":\n    main()', 'main()')


def main():
    md, code = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
    earlier = nbformat.read(ROOT / "submission/receiver_speed_translation.ipynb", as_version=4)
    setup = next(cell.source for cell in earlier.cells if cell.cell_type == "code")
    cells = [md("""# The Fastest Part Is the Exit
## Phase-Aware Validation of Offensive Line Combine Tracking Across Drills, Movements, and Rookie Pass Protection

**Methodological & Scouting Validation Study (NFL Big Data Bowl 2027).** This notebook
rebuilds the complete offensive line (C/G/T) Combine phase-segmentation audit across
all three OL footwork drills (`Pass-Pro Mirror Drill`, `5-Yard Wave Drill`, and
`Pass Rush Drop` — 470 accepted recordings), two-attempt trial repeatability bounds,
rookie one-on-one pass-protection out-of-time modeling (across binary pressure allowed
and continuous Next Gen Stats peak pressure probability), same-axis early-game lateral
movement transfer (`0–1.5 s`), and 400-replicate full-refit player bootstrap uncertainty.

CPU only; no external data or internet required. Attach the competition dataset and
run all cells. Physical Next Gen Stats tracking units are verified across the pipeline
(`x, y` in `yards`, `s` in `yd/s`, `a` in `yd/s²`, `10 Hz` sampling).
"""), code(setup), md("""## 1. Rookie Offensive Line Cohort Metadata

We restrict to offensive linemen (`C`, `G`, `T`) in their rookie regular season on
non-nullified plays. The downstream pass-protection analysis retains `C/G/T` game
alignments, an observed `pressure_allowed` and `peak_pressure_probability_allowed`
label, **exactly one encountered pass rusher**, and at least `100` eligible one-on-one
opportunities per player (`50` players, `20,853` snaps, `1,850` pressures).
"""), code(source("prepare_ol_metadata.py")), md("""## 2. Segment Functional Footwork from the Exit Sprint Across All Three OL Drills

Both spelling variants of the Mirror drill (`PASS_PRO-MIRROR_DRILL` and
`PASS_PRO_MIRROR_DRILL`) are combined. A sustained forward departure of `1.5 yards`
for four consecutive frames (`0.4 s`) relative to the initial five-frame median $x_0$
anchor defines exit onset. We require strictly increasing `10 Hz` timestamps with no
frame gaps above `0.21 s`, at least `3.0 seconds` of mirror tracking, and at least
two detected lateral reversals (`113` accepted players/attempts).

Five-frame quadratic Savitzky–Golay smoothing of $y(t)$ precedes differentiation to
compute lateral velocity $v_y(t)$ (`yd/s`). The two predeclared mirror-phase features
are `lateral_speed_p75` (75th percentile of $|v_y(t)|$ in `yd/s`) and
`reversal_recovery` (median ratio of post-turn to pre-turn lateral speed). We compare
these against `whole_drill_speed` (95th percentile of 3-frame median-smoothed total
speed $s(t)$ across the full recording).

We also audit `FIVE_YARD_WAVE_DRILL_SLIDE_AND_SHUFFLE` (`118` attempts) and
`PASS_RUSH_DROP` (`239` attempts, including `118` OL with two tracked repetitions)
to test whether exit-sprint dominance is universal across OL Combine drills and to
quantify trial-to-trial repeatability.
"""), code(source("extract_mirror_features.py")), md("""## 3. Out-of-Time Validation: Rookie One-on-One Pass Protection

The classic player baseline uses official `40-yard dash`, `10-yard split`,
`combine_weight`, `arm_length`, and position (`C/G/T`). We compare `Classic Combine`
alone, `Classic + Whole-Drill Speed`, and `Classic + Mirror-Phase Features` using
fixed `Ridge(alpha=10)` models under strict forward-year evaluation (`2023 -> 2024`
and `2023–2024 -> 2025`), with training-only imputation, scaling, and play-context
adjustment (`lined_up_position`, `offense_formation`, `down`, `yards_to_go`,
`dropback_duration`, and `duration_sq`).

Three outcome specifications are evaluated side-by-side:
1. **Primary (`primary_with_duration`):** Binary `pressure_allowed` adjusted for play context including dropback duration.
2. **Predeclared Sensitivity (`sensitivity_without_duration`):** Binary `pressure_allowed` without dropback duration.
3. **Continuous NGS Outcome (`continuous_pressure_probability`):** Context-adjusted `peak_pressure_probability_allowed` (where game split-half reliability increases from `r = 0.367` to `r = 0.696`).
"""), code(source("analyze_mirror_protection.py")), code("""display(Image(filename=str(WORK_DIR / 'reports/trenches/mirror_model_comparison.png')))
display(pd.read_csv(WORK_DIR / 'reports/trenches/mirror_forward_year_scores.csv'))
"""), md("""## 4. Intermediate Construct Validation: Early-Game Lateral Speed (0–1.5 s)

Specified after observing the primary pressure results, this check tests whether
Combine mirror lateral speed transfers directly to on-field lateral speed during the
first `1.5 seconds` after snap (`20,110` valid plays across the `50` linemen, `>= 50`
plays per player), using the exact same Savitzky–Golay differentiation (`yd/s`) and
training-only context adjustment (`lined_up_position`, `offense_formation`, `down`,
`yards_to_go`, `snap_speed`).
"""), code(source("extract_ol_movement.py")), code(source("analyze_ol_movement.py")), code("""display(Image(filename=str(WORK_DIR / 'reports/trenches/movement_bridge_results.png')))
display(pd.read_csv(WORK_DIR / 'reports/trenches/movement_forward_year_scores.csv'))
"""), md("""## 5. Diagnostic Visualization and Bilingual Interactive Explorer

Within-class percentile comparisons (`Spearman r = +0.005`) demonstrate that
exit-contaminated whole-drill speed and isolated mirror lateral speed produce nearly
orthogonal rankings. This section generates `mirror_phase_story.png`,
`mirror_ranking_shift.png`, and the standalone bilingual (`TR` / `EN`) interactive
explorer `mirror_explorer.html` covering all `113` accepted offensive linemen.
"""), code(source("mirror_measurement_report.py")), code("""display(Image(filename=str(WORK_DIR / 'reports/trenches/mirror_phase_story.png')))
display(Image(filename=str(WORK_DIR / 'reports/trenches/mirror_ranking_shift.png')))
"""), md("""## 6. Physical Invariance Checks and 400-Replicate Full-Refit Bootstrap

Seven synthetic checks verify exact invariance to coordinate translation, lateral
reflection, timestamp origin, and input row ordering, plus rejection of duplicate or
gapped frames and detection of synthetic reversals. The 2025 full-refit bootstrap
resamples whole training players within class and test players across `400`
replicates, refitting both play-context and player ridge models in every replicate.
"""), code(source("validate_mirror_study.py")), md("""## Summary & Practical Takeaways for NFL Front Offices

1. **Universal Exit-Sprint Contamination (`470 / 470` OL Recordings):** Across `Pass-Pro Mirror` (`113/113`), `5-Yard Wave` (`118/118`), and `Pass Rush Drop` (`239/239`), maximum smoothed speed always occurs in the finishing sprint rather than the lateral or pass-set phase.
2. **Repeatability Explains Attenuation:** In two-attempt `Pass Rush Drop` data (`n = 118` paired OL), exit sprint speed repeats at `r = +0.510`, whereas reactive pass-set lateral speed repeats at `r = +0.104`, bounding downstream game correlations.
3. **Honest Out-of-Time Validation:** Removing the exit sprint prevents `whole_drill_speed` from degrading 2025 pass-protection predictions, but single-rep mirror features do not achieve statistically significant out-of-time improvements over classic Combine measurements (`2025` full-refit 95% CI: `[−0.264, +0.353]` percentage points).

Sources: [NFL Big Data Bowl 2027](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027),
[Offensive Line Combine Drill Coaching Guide](https://coachesinsider.com/football/offensive-linemen-specific-combine-drills/).
""")]
    output = ROOT / "submission_mirror"
    output.mkdir(exist_ok=True)
    notebook = nbformat.v4.new_notebook(cells=cells, metadata={
        "kernelspec": {"name": "python3", "language": "python", "display_name": "Python 3"},
        "language_info": {"name": "python", "version": "3.10"}})
    nbformat.validate(notebook)
    nbformat.write(notebook, output / "mirror_phase_validation.ipynb")
    print(f"Built mirror notebook: {len(cells)} cells")


if __name__ == "__main__":
    main()
