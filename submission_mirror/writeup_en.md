# The Fastest Part Is the Exit
## Phase-Aware Validation of Offensive Line Combine Tracking Across Drills, Movements, and Rookie Pass Protection

### A Football Question Hiding Inside a Measurement Choice

The NFL Scouting Combine’s offensive line footwork drills—led by the **Pass-Pro Mirror Drill**, alongside the **5-Yard Wave Drill** and **Pass Rush Drop**—are designed to evaluate short-area lateral agility, balance, and change-of-direction recovery. Yet a tracking recording captures everything between whistle and stop, not just the intended football task.

Auditing the competition’s Next Gen Stats (NGS) Combine tracking data (`10 Hz`, coordinates in `yards`, speed in `yd/s`) reveals a striking measurement trap: **in 100.0% of accepted recordings across all three offensive line footwork drills (470 of 470 attempts), a lineman’s highest speed occurs during the finishing exit sprint**, after the lateral mirror or pass-set footwork has ended.

This raises a practical question for NFL front offices: *when we rank offensive line prospects using Combine drill speed metrics, are we evaluating pass-protection footwork—or accidentally re-measuring straight-line sprint speed?*

We address this question with a four-stage validation funnel:
1. **Phase Isolation & Multi-Drill Audit:** We segment functional footwork from the finishing sprint across all three OL Combine drills (`470` attempts) and verify physical invariance and boundary robustness.
2. **Ranking Shift & Trial Repeatability:** We quantify how exit-sprint contamination distorts within-class rankings and use two-attempt `Pass Rush Drop` data ($n = 118$ paired linemen) to establish trial-to-trial repeatability bounds.
3. **Out-of-Time Pass-Protection Prediction:** Across **50 rookie offensive linemen and 20,853 one-on-one pass-protection snaps**, we test whether phase-isolated mirror features add out-of-time predictive value beyond classic Combine metrics (`40-yard dash`, `10-yard split`, `weight`, `arm length`), evaluating both binary `pressure_allowed` and continuous NGS `peak_pressure_probability_allowed`.
4. **Same-Axis Early-Game Transfer:** We test whether Combine lateral speed transfers directly to early-game lateral movement (`0–1.5 s` post-snap across `20,110` plays).

Our conclusion is two-fold: **phase segmentation is mandatory** because whole-drill speed metrics completely misrank lateral footwork ($r_s = +0.005$), while **rigorous out-of-time validation prevents false scouting claims**, showing that single-rep coach-cued drill features do not reliably beat classic Combine baselines in predicting rookie pass protection (`2025` full-refit 95% CI: `[−0.264, +0.353]` percentage points).

---

### 1. Isolate the Football Task Before Computing the Feature

In the `Pass-Pro Mirror Drill`, an offensive lineman slides laterally to mirror a coach before finishing with a forward sprint (`+x`). Combining both spelling variants (`PASS_PRO-MIRROR_DRILL` and `PASS_PRO_MIRROR_DRILL`), `121` offensive linemen (`C`, `G`, `T`) have tracking recordings across the 2023–2025 draft classes.

We establish a predeclared geometric segmentation rule prior to outcome modeling:
- **Exit Onset:** The first frame where forward displacement exceeds `1.5 yards` relative to the initial five-frame median anchor ($x_0$) for four consecutive frames (`0.4 s`).
- **Quality Filters:** Strictly increasing `10 Hz` timestamps with no gaps above `0.21 s`, at least `3.0 s` of pre-exit mirror tracking, and at least two valid lateral direction reversals. This yields **113 accepted recordings (113 linemen)**; eight fail the reversal requirement.
- **Kinematics & Features:** Lateral coordinates $y(t)$ are smoothed with a five-frame quadratic Savitzky–Golay filter before differentiation into lateral velocity $v_y(t)$ (`yd/s`). The two predeclared mirror-phase features are:
  1. **Mirror Lateral Speed (`lateral_speed_p75`):** 75th percentile of $|v_y(t)|$ during the mirror phase (`yd/s`).
  2. **Post-Reversal Recovery Ratio (`reversal_recovery`):** Median ratio of mean $|v_y(t)|$ `0.3–0.6 s` after a reversal to mean $|v_y(t)|$ `0.5–0.2 s` before the reversal.
- **Whole-Drill Comparison (`whole_drill_speed`):** 95th percentile of three-frame median-smoothed total speed $s(t)$ (`yd/s`) over the full recording.

![Figure 1. Field trajectories (top, in yards) and speed profiles (bottom, in yd/s) for the first accepted lineman by ID in each draft class. Across all 113 accepted Mirror Drill recordings, global peak speed occurs during the finishing exit sprint rather than the lateral mirror phase.](figures/mirror_phase_story.png)

In **113 of 113 accepted Mirror recordings (100.0%)**, global peak speed occurs after the `1.5-yard` exit threshold (`Figure 1`). Varying the exit boundary to `1.0` or `2.0 yards` leaves player rankings virtually unchanged (`Spearman r = 0.992` and `0.998` for `lateral_speed_p75`; `1.000` and `0.999` for `reversal_recovery`), and seven synthetic checks verify exact invariance to coordinate translation, lateral reflection, timestamp shifts, and row reordering.

Extending phase segmentation across the entire offensive line Combine footwork suite confirms that exit-sprint dominance is universal (`Table 1`):

| Offensive Line Combine Drill | Accepted Reps (Players) | Functional Footwork Phase | Peak Speed in Exit Sprint | Phase Lateral vs. Whole-Drill Speed ($r_s$) |
|---|---:|---|---:|---:|
| **Pass-Pro Mirror Drill** | 113 (113 OL) | Lateral mirror slide (`y` axis) | **100.0% (113 / 113)** | **+0.005** |
| **5-Yard Wave Drill (Slide & Shuffle)** | 118 (118 OL) | Multi-directional shuffle prior to `-2.0 yd` exit | **100.0% (118 / 118)** | **−0.022** |
| **Pass Rush Drop (Kick-Slide)** | 239 (120 OL) | Diagonal pass-set drop prior to `2.2 yd` finish | **100.0% (239 / 239)** | **+0.147** |

Across all **470 accepted recordings**, peak speed occurs in the finishing sprint every single time. Among the `109` linemen who completed all three drills, whole-recording speeds correlate positively across drills (`Wave vs. Drop` $r_s = +0.406$; `Mirror vs. Drop` $r_s = +0.296$) solely because all three capture straight-line finishing speed, whereas isolated lateral speeds show weak cross-drill agreement ($r_s = -0.005\text{ to }+0.224$).

---

### 2. Re-Ranking Consequences and Trial Repeatability Bounds

Because whole-drill speed measures the exit sprint while mirror lateral speed measures lateral footwork, the two metrics produce nearly orthogonal rankings (`pooled Spearman r = +0.005`; within-class $r_s = -0.046, +0.268, -0.283$ in 2023, 2024, and 2025).

Within-class percentile rankings shift by a median of **32.4, 21.4, and 32.4 percentage points** across the three classes (`Figure 2A`). In 2025, each metric places nine linemen into the top quartile (`≥75th percentile`), but **only one lineman belongs to both top quartiles**. Prominent NFL starters and first-round prospects experience massive percentile reversals depending on whether the exit sprint is removed—including **Donovan Jackson** (`2.9th` whole-drill percentile vs. `94.1st` mirror lateral percentile, `+91.2 pp`), **Dominick Puni** (`7.1st` vs. `95.2nd`, `+88.1 pp`), **Darnell Wright** (`97.3rd` vs. `8.1st`, `−89.2 pp`), and **Tyler Booker** (`100.0th` vs. `5.9th`, `−94.1 pp`).

![Figure 2. Left: Within-class percentile re-ranking between exit-contaminated whole-drill speed and isolated mirror lateral speed (Spearman r = +0.005). Right: Universal 100% exit-sprint peak dominance and near-zero phase rank agreement across all three offensive line Combine footwork drills (470 total recordings).](figures/mirror_ranking_shift.png)

Why should an analyst remain cautious before using isolated lateral speed as a standalone draft grade? While the Mirror drill has only one attempt per player, **118 offensive linemen recorded two tracked attempts in `Pass Rush Drop`** (`Figure 2B`). Across paired repetitions:
- **Whole-drill speed (the exit sprint)** is moderately repeatable: `Pearson r = +0.510` (`Spearman r = +0.510`).
- **Pass-set lateral speed** has low trial-to-trial repeatability: `Pearson r = +0.104` (`Spearman r = +0.120`; kick-slide depth speed `r_s = +0.230`).

Unlike a self-paced `40-yard dash` (where WR peak speed repeats at `r = 0.893` in our companion study), OL footwork drills are paced by coaches or unstandardized visual cues. By psychometric attenuation ($r_{XY} \le \sqrt{r_{XX} \cdot r_{YY}}$), low trial repeatability ($r_{XX} \approx 0.10\text{–}0.23$) mathematically bounds how strongly single-rep drill footwork can correlate with NFL outcomes.

---

### 3. Out-of-Time Validation on Rookie One-on-One Pass Protection

We link the accepted Mirror cohort to rookie regular-season NFL performance on non-nullified plays where the lineman aligned at `C`, `G`, or `T`, encountered **exactly one pass rusher**, and accrued at least `100` one-on-one opportunities. This yields **50 rookie linemen (`17` in 2023, `16` in 2024, `17` in 2025), 20,853 snaps, and 1,850 pressures allowed**.

All context adjustments, median imputations, and scalers are fit strictly on training classes (`2023 → 2024` and `2023–2024 → 2025`), with zero player overlap. We evaluate three outcome specifications (`Table 2` and `Figure 3`):
1. **Primary Outcome (Binary `pressure_allowed`, Duration-Adjusted):** Training-only logistic regression adjusts for lineup (`C/G/T`), formation, down, yards to go, dropback duration, and duration squared. Each player’s target is mean observed-minus-expected pressure (`pp`).
2. **Predeclared Sensitivity (Binary `pressure_allowed`, No Duration):** Removes dropback duration.
3. **Continuous Outcome Sensitivity (`peak_pressure_probability_allowed`):** Binary pressure has modest alternating-game split-half reliability (`r = 0.367`). Continuous NGS `peak_pressure_probability_allowed` nearly doubles split-half game reliability to **`r = 0.696`**, providing a lower-noise test of predictive transfer.

Fixed `Ridge(alpha=10)` player models compare **Classic Combine** (`40-yard dash`, `10-yard split`, `weight`, `arm length`, plus position), **Classic + Whole-Drill Speed**, and **Classic + Mirror-Phase Features**:

| Outcome Specification | Test Class ($n$) | Mean Ref MAE | Classic Combine MAE | + Whole-Drill Speed (Exit) | + Mirror-Phase Features | Mirror vs. Classic $\Delta$ MAE (95% CI) |
|---|---:|---:|---:|---:|---:|---:|
| **Primary: Binary Pressure (Duration-Adj.)** | 2024 ($16$) | 1.971 | 1.972 | 1.922 | **1.909** | +0.062 pp `[−0.171, +0.332]` |
| **Primary: Binary Pressure (Duration-Adj.)** | 2025 ($17$) | **2.405** | 2.502 | 2.652 | 2.482 | +0.019 pp `[−0.105, +0.135]` |
| **Sensitivity: Binary Pressure (No Duration)** | 2024 ($16$) | 1.996 | 1.876 | **1.871** | 1.888 | −0.012 pp `[−0.123, +0.103]` |
| **Sensitivity: Binary Pressure (No Duration)** | 2025 ($17$) | **2.325** | 2.351 | 2.446 | 2.365 | −0.014 pp `[−0.110, +0.081]` |
| **Continuous: Peak Pressure Probability** | 2024 ($16$) | 2.107 | 2.101 | **2.087** | 2.113 | −0.011 pp `[−0.205, +0.186]` |
| **Continuous: Peak Pressure Probability** | 2025 ($17$) | 2.164 | 2.189 | 2.215 | **2.157** | +0.032 pp `[−0.139, +0.195]` |

![Figure 3. Out-of-time rookie one-on-one pass-protection prediction error (player MAE in percentage points) across three outcome specifications: primary duration-adjusted binary pressure, predeclared sensitivity without duration adjustment, and continuous Next Gen Stats peak pressure probability allowed.](figures/mirror_model_comparison.png)

Three empirical lessons emerge:
- **Exit-contaminated whole-drill speed degrades 2025 prediction across every specification** (`2.502 → 2.652 pp` primary; `2.351 → 2.446 pp` no-duration; `2.189 → 2.215 pp` continuous probability).
- **Phase-isolated mirror features directionalize correctly in 2025** on primary binary pressure (`2.502 → 2.482 pp`) and continuous pressure probability (`2.189 → 2.157 pp`, RMSE `2.639 → 2.532 pp`), confirming that removing the exit sprint eliminates misleading noise.
- **Incremental predictive gains remain statistically indistinguishable from zero.** Resampling training players within class and test players and refitting both models across `400` bootstrap replicates yields a 2025 primary improvement interval of **`[−0.264, +0.353] pp`**, and in binary specifications the training-mean baseline achieves the lowest 2025 MAE.

---

### 4. Construct Check: Early-Game Lateral Speed Transfer

Extracting the first `1.5 seconds` after snap across **20,110 valid pass-protection plays** (`≥50` per lineman) with the same Savitzky–Golay differentiation (`yd/s`) shows that a lineman’s early-game lateral speed is highly reliable across games (**split-half `r = 0.797`**), yet correlates weakly with Combine mirror lateral speed (**`r = 0.053` pooled**; **`r = 0.120` within year and position**) and does not reduce forward-year MAE (`0.0916 → 0.0923 yd/s` in 2024; `0.1070 → 0.1087 yd/s` in 2025). In games, early lateral velocity reflects blocking assignment and rusher alignment rather than unconstrained maximum lateral speed.

---

### 5. Actionable Recommendations for NFL Teams and Combine Design

1. **Gate Combine Pipelines by Movement Phase, Not Filename:** Isolate the lateral or pass-set phase prior to the `1.5–2.2 yard` exit sprint and inspect trajectories visually (`mirror_explorer.html`).
2. **Standardize Reactive Cues and Collect Multi-Rep Baselines:** Replacing variable human mirror leads with standardized light/screen cues and recording at least two mirror attempts per prospect will directly raise trial repeatability above `r = 0.104`.
3. **Require Four-Stage Validation Before Adjusting Draft Grades:** Demand phase isolation, multi-rep reliability, same-axis game transfer, and out-of-time incremental prediction over classic Combine baselines.

### Reproducibility and Sources

All tables, figures, invariance checks, and the interactive explorer run on CPU from the [NFL Big Data Bowl 2027 CSVs](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027) with zero external data. Drill context follows [Landow & Jarmon’s coaching guide](https://coachesinsider.com/football/offensive-linemen-specific-combine-drills/).
