"""Forward-year check: do similar Combine profiles help predict a rookie movement measure?

Uses the recorded, versioned research tables only. Settings were fixed before the first run.
Run from the repository root: python -m scripts.evaluate_similarity [--check]
"""
import argparse
import csv
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np

from app.similarity import GROUPS, K, MIN_SHARED_FEATURES, MIN_SHARED_FRACTION, nearest, fit_scaler, number

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports" / "similarity"
SETTINGS = {
    "primary_k": K, "sensitivity_k": [3, 7], "ridge_alpha": 10.0,
    "min_shared_features": MIN_SHARED_FEATURES, "min_shared_fraction": MIN_SHARED_FRACTION,
    "bootstrap_resamples": 2000, "seed": 20270108,
    "folds": [[[2023], 2024], [[2023, 2024], 2025]],
    "primary_metric": "player-level mean absolute error",
}
STUDIES = {
    "WR": {"file": "reports/speed_study/descriptive_player_means.csv", "target": "game_peak_speed",
           "label": "Çaylak sezonu rota zirve hızı (veri birimi)"},
    "OL": {"file": "reports/trenches/movement_player_means.csv", "target": "game_lateral_speed_p75",
           "label": "Çaylak sezonu erken yanal hız (veri birimi)"},
}


def text_hash(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load(study):
    features = GROUPS[study]["features"]
    with (ROOT / STUDIES[study]["file"]).open(encoding="utf-8-sig", newline="") as stream:
        rows = []
        for raw in csv.DictReader(stream):
            row = {name: number(raw[name]) for name in features}
            row.update(nfl_id=int(raw["nfl_id"]), draft_year=int(raw["draft_year"]),
                       nfl_position=raw["nfl_position"], target=float(raw[STUDIES[study]["target"]]))
            rows.append(row)
    return sorted(rows, key=lambda row: row["nfl_id"])


def ridge(train, test, features, alpha):
    """Median imputation and scaling are fitted on the training players only."""
    def matrix(rows):
        return np.array([[np.nan if row[name] is None else row[name] for name in features] for row in rows], float)

    x, z = matrix(train), matrix(test)
    usable = [i for i in range(x.shape[1]) if np.isfinite(x[:, i]).any()]
    x, z = x[:, usable], z[:, usable]
    median = np.nanmedian(x, axis=0)
    x, z = np.where(np.isnan(x), median, x), np.where(np.isnan(z), median, z)
    mean, deviation = x.mean(axis=0), x.std(axis=0)
    deviation[deviation == 0] = 1
    x, z = (x - mean) / deviation, (z - mean) / deviation
    y = np.array([row["target"] for row in train])
    weights = np.linalg.solve(x.T @ x + alpha * np.eye(x.shape[1]), x.T @ (y - y.mean()))
    return y.mean() + z @ weights


def neighbours(train, test, features, k):
    scaler = fit_scaler(train, features)
    mean = float(np.mean([row["target"] for row in train]))
    predictions, fallbacks = [], 0
    for row in test:
        matches = nearest(row, train, features, k, scaler)
        if len(matches) < k:
            predictions.append(mean)
            fallbacks += 1
        else:
            predictions.append(float(np.mean([match["row"]["target"] for match in matches])))
    return np.array(predictions), fallbacks


def position_mean(train, test):
    overall = np.mean([row["target"] for row in train])
    values = {}
    for row in train:
        values.setdefault(row["nfl_position"], []).append(row["target"])
    return np.array([np.mean(values[row["nfl_position"]]) if row["nfl_position"] in values else overall
                     for row in test])


def predict(train, test, features):
    mean = np.full(len(test), np.mean([row["target"] for row in train]))
    models = {"mean": mean, "position_mean": position_mean(train, test),
              "ridge": ridge(train, test, features, SETTINGS["ridge_alpha"])}
    fallbacks = {}
    for k in [SETTINGS["primary_k"], *SETTINGS["sensitivity_k"]]:
        models[f"similar_k{k}"], fallbacks[f"similar_k{k}"] = neighbours(train, test, features, k)
    return models, fallbacks


def evaluate(rows, features, train_years, test_year):
    if max(train_years) >= test_year:
        raise ValueError("Training classes must precede the test class.")
    train = [row for row in rows if row["draft_year"] in train_years]
    test = [row for row in rows if row["draft_year"] == test_year]
    actual = np.array([row["target"] for row in test])
    models, fallbacks = predict(train, test, features)
    errors = {name: np.abs(values - actual) for name, values in models.items()}
    rng = np.random.default_rng(SETTINGS["seed"] + test_year)
    improvements = {name: [] for name in models if name != "mean"}
    for _ in range(SETTINGS["bootstrap_resamples"]):
        # Refit on resampled training players and score resampled test players.
        sampled = [train[i] for i in rng.integers(len(train), size=len(train))]
        chosen = rng.integers(len(test), size=len(test))
        refit, _ = predict(sampled, test, features)
        base = np.abs(refit["mean"] - actual)[chosen].mean()
        for name, values in improvements.items():
            values.append(base - np.abs(refit[name] - actual)[chosen].mean())
    scores = []
    for name, error in errors.items():
        score = {"model": name, "mae": error.mean(), "rmse": np.sqrt((error ** 2).mean()),
                 "fallback_players": fallbacks.get(name, 0)}
        if name != "mean":
            low, high = np.quantile(improvements[name], [.025, .975])
            score.update(improvement_over_mean=errors["mean"].mean() - error.mean(), ci_low=low, ci_high=high)
        scores.append({key: round(float(value), 6) if isinstance(value, (float, np.floating)) else value
                       for key, value in score.items()})
    return {"train_years": train_years, "test_year": test_year,
            "train_players": len(train), "test_players": len(test), "scores": scores}


def run():
    studies = {}
    for name, rule in STUDIES.items():
        rows, features = load(name), GROUPS[name]["features"]
        studies[name] = {
            "target": rule["target"], "target_label": rule["label"], "players": len(rows),
            "features": list(features),
            "missing": {f: sum(row[f] is None for row in rows) for f in features},
            "folds": [evaluate(rows, features, years, test) for years, test in SETTINGS["folds"]],
        }
    inputs = {rule["file"]: text_hash(ROOT / rule["file"]) for rule in STUDIES.values()}
    primary = f"similar_k{SETTINGS['primary_k']}"
    consistent = all(
        next(s for s in fold["scores"] if s["model"] == primary)["ci_low"] > 0
        for study in studies.values() for fold in study["folds"])
    return {
        "status": "exploratory", "settings": SETTINGS, "inputs_sha256": inputs,
        "data_version": hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest(),
        "code_sha256": {p: text_hash(ROOT / p) for p in ("app/similarity.py", "scripts/evaluate_similarity.py")},
        "studies": studies, "consistent_benefit_shown": consistent,
        "independent_validation": "not_performed",
        "limitations": [
            "Örneklemler küçüktür: testlerde yalnızca 16–20 oyuncu vardır.",
            "Aynı oyuncu ve yılların sonuçları önceki araştırmalarda incelenmiştir; bu analiz keşifseldir.",
            "Yeni sezon veya bağımsız oyuncu örneklemi bulunmadığından bağımsız doğrulama yapılmamıştır.",
            "Ham yarışma CSV'leri bu çalışmada yoktu; sonuçlar kayıtlı araştırma tablolarından hesaplanmıştır.",
            "Hedefler hareket ölçümleridir; genel oyuncu başarısı değildir.",
            "Yalnızca Combine'a katılan ve maç kaydı bulunan oyuncular dahildir; bu seçim yanlılığı yaratabilir.",
            "Çoklu model ve k değeri için düzeltme yapılmamıştır.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="compare with the recorded result; write nothing")
    args = parser.parse_args()
    result = run()
    path = OUTPUT / "summary.json"
    if args.check:
        recorded = json.loads(path.read_text(encoding="utf-8"))
        recorded.pop("environment", None)
        if recorded != json.loads(json.dumps(result)):
            raise SystemExit("Recorded similarity result does not match a fresh run.")
        print("Recorded result reproduced.")
        return
    result["environment"] = {"python": platform.python_version(), "numpy": np.__version__}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    manifest = {"verification": {"status": "passed"}, "files": [
        {"path": "reports/similarity/summary.json", "sha256": text_hash(path)}]}
    (OUTPUT / "manifest.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    for name, study in result["studies"].items():
        for fold in study["folds"]:
            print(name, fold["test_year"], f"train={fold['train_players']} test={fold['test_players']}")
            for score in fold["scores"]:
                print("  ", score)
    print("consistent benefit:", result["consistent_benefit_shown"])


if __name__ == "__main__":
    sys.exit(main())
