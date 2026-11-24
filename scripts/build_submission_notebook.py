"""Build a standalone Kaggle notebook from the reproducible analysis scripts."""
from pathlib import Path
import nbformat

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "submission"


def source(name):
    text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
    text = text.replace('ROOT = Path(__file__).resolve().parents[1]', 'ROOT = WORK_DIR')
    text = text.replace('DATA = ROOT / "data/nfl-big-data-bowl-2027"', 'DATA = DATA_DIR')
    text = text.replace('from analyze_speed_transfer import context_model, player_model, CAT, NUM, BASE\n', '')
    text = text.replace('if __name__ == "__main__":\n    main()', 'main()')
    return text


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    md, code = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
    cells = [md("""# Repeatable Speed, Uncertain Added Value
## Combine tracking to rookie receiver route speed

**Question:** Do tracking-derived 40-yard features add information beyond official
40-yard time, height and weight when predicting rookie receivers' in-game route speed?

This notebook reproduces the full analysis from the nine competition CSV files.
It streams the large game files in chunks, needs no internet, and uses CPU only.
Attach the **NFL Big Data Bowl 2027** competition data and run all cells.
No external datasets or pretrained models are used.

**Scope:** This is exploratory research, not a claim of overall player quality.
Earlier curl-to-separation analyses did not demonstrate incremental predictive value.
This speed analysis retains both evaluation years and its unsuccessful checks.
"""), code("""import os
from pathlib import Path
import platform
import numpy as np
import pandas as pd
import sklearn
from IPython.display import display, Image, Markdown

if os.environ.get('NFL_DATA_DIR'):
    DATA_DIR = Path(os.environ['NFL_DATA_DIR'])
else:
    candidates = [Path.cwd() / 'data/nfl-big-data-bowl-2027',
                  Path.cwd().parent / 'data/nfl-big-data-bowl-2027']
    DATA_DIR = next((p for p in candidates if (p / 'players.csv').exists()), None)
    if DATA_DIR is None and Path('/kaggle/input').exists():
        matches = list(Path('/kaggle/input').rglob('combine_tracking.csv'))
        if len(matches) != 1:
            raise RuntimeError('Attach exactly one competition dataset, or set NFL_DATA_DIR.')
        DATA_DIR = matches[0].parent
    if DATA_DIR is None:
        raise FileNotFoundError('Competition CSVs not found; set NFL_DATA_DIR to their directory.')

WORK_DIR = Path(os.environ.get('NFL_WORK_DIR', '/kaggle/working' if Path('/kaggle').exists()
                            else str(Path.cwd() / 'notebook_output')))
WORK_DIR.mkdir(parents=True, exist_ok=True)
required = ['players.csv', 'combine_results.csv', 'combine_tracking.csv', 'games.csv',
            'player_play.csv'] + [f'game_tracking_{y}.csv' for y in (2023, 2024, 2025)]
assert all((DATA_DIR / f).is_file() for f in required), 'Missing competition files'
print({'python': platform.python_version(), 'numpy': np.__version__,
       'pandas': pd.__version__, 'sklearn': sklearn.__version__,
       'data_directory': str(DATA_DIR), 'output_directory': str(WORK_DIR)})
"""), md("""## 1. Fixed primary design and measurement

We use wide receivers' **rookie regular seasons**, not cumulative careers. The
game outcome is the 95th percentile of a three-frame median-smoothed speed stream
from snap until the throw, capped at four seconds. A play needs a route label,
one snap, one throw, at least two seconds and twenty frames, no duplicate timestamps
or gaps above 0.21 seconds, and no nullifying penalty. The player must have at least
30 accepted plays and tracked 40-yard data.

Combine peak speed uses the same smoothing and percentile. The early-speed proxy
is speed one second after the first observed speed of at least 1 in the supplied
units. Both features are median-aggregated across attempts. This is **not an official
timed acceleration split**. We record attempts that already start above the threshold.

Before any speed-outcome results were computed, the windows, features, sample threshold,
models and year splits were recorded in the project design. Next Gen Stats tracking
coordinates are in `yards` and speeds in `yd/s` (`10 Hz`), with coordinate-derived
speeds matching supplied speed at a median ratio of `0.99`.
"""), code(source("extract_speed_data.py")), md("""## 2. Forward-year evaluation

Train on 2023 to evaluate 2024; train on 2023–2024 to evaluate 2025. Players never
cross train/test. A training-only ridge model adjusts each play's speed for route,
coverage, window duration and its square, snap speed and cushion. Each player's
mean residual is the prediction target. This is a contextual speed measure,
not separation, receiving production or a causal ability score.

Compare a training-mean reference, official 40 time + height + weight, and those
three features plus the two tracking measures. All ridge penalties are fixed at
10; imputation and scaling use training data only. Each player has equal evaluation
weight. Report MAE and RMSE, with a paired player-bootstrap interval on the MAE
improvement. These intervals condition on fitted models and omit training uncertainty.
"""), code(source("analyze_speed_transfer.py")), code("""display(pd.read_csv(WORK_DIR / 'reports/speed_study/forward_year_scores.csv'))
display(Image(filename=str(WORK_DIR / 'reports/speed_study/speed_transfer_results.png')))
display(Image(filename=str(WORK_DIR / 'reports/speed_study/game_speed_reliability.png')))
"""), md("""## 3. Clearly labelled post-hoc diagnostics

After inspecting the primary results, we examine within-year associations, paired
Combine attempts, and a single ablation that removes the low-repeatability early-speed
proxy. These are descriptive/diagnostic checks, not a replacement primary analysis
or new independent validation. All checked years are retained.
"""), code(source("speed_robustness.py")), code("""display(Image(filename=str(WORK_DIR / 'reports/speed_study/combine_repeatability.png')))
display(pd.read_csv(WORK_DIR / 'reports/speed_study/correlation_diagnostics.csv'))
display(pd.read_csv(WORK_DIR / 'reports/speed_study/post_hoc_peak_only_ablation.csv'))
"""), md("""## 4. Interpretation and limitations

The observed Combine-to-game speed association and high peak-speed repeatability
are useful measurement findings. They do not establish an improvement over existing
scouting measurements: the primary added-feature improvement appears in 2024 but
does not repeat in 2025. Both conditional intervals include zero.

The peak feature overlaps strongly with official 40-yard time. The early-speed proxy
is much less repeatable and depends on an approximate start. Even the post-hoc
peak-only model does not consistently improve MAE. Keep the distinction between
**repeatability**, **association with game movement**, and **incremental prediction**.

For teams: use this as a measurement-validation template before assigning scouting
weight to a new metric. We do not recommend a new player ranking from these results.
Route speed is limited by tactical assignment and opportunity; remaining route-depth,
team and opponent effects are not removed by the additive context model. The sample
excludes nonparticipants and players with few eligible rookie routes; longer-developing
pass plays are preferentially retained. There are only 20 and 16 test players. Prior
exploration used these draft classes, so none is a pristine confirmatory holdout.

The source project retains the earlier curl/separation null results and a complete
experiment register. A separate English writeup reports the numerical conclusions.

### Sources and related work
- [Competition and data](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027)
- [NFL official announcement](https://www.nfl.com/news/big-data-bowl-returns-powered-by-aws)
- [Host discussion on 40-yard tracking timing](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/discussion/751371)
- [Public-work survey: data traps and open angles](https://hackers.pocketplay.win/en/kaggle/nfl-big-data-bowl-2027/)

The public-work survey was consulted after the primary speed results; it describes
prior investigations of start-timing and repeatability. Those ideas are not claimed
as novel here. No public-notebook predictions or derived features were imported.
""")]
    nb = nbformat.v4.new_notebook(cells=cells, metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
    })
    nbformat.validate(nb)
    destination = DEST / "receiver_speed_translation.ipynb"
    nbformat.write(nb, destination)
    print(f"Wrote {destination}, {len(cells)} cells")


if __name__ == "__main__":
    main()
