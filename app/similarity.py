"""Position-aware similarity of Combine profiles.

Only physical Combine measurements are compared. Draft position, NGS scores, career
totals and game outcomes are deliberately excluded. Similarity is descriptive and is
not a forecast of equal success.
"""
import math

K = 5
MIN_POOL = 10
MIN_SHARED_FRACTION = 0.6
MIN_SHARED_FEATURES = 4

GROUPS = {
    "OL": {"positions": ("C", "G", "T"), "features": (
        "combine_height", "combine_weight", "arm_length", "ten_yd_split",
        "vertical", "broad_jump", "short_shuttle")},
    "WR": {"positions": ("WR",), "features": (
        "combine_height", "combine_weight", "arm_length", "ten_yd_split",
        "forty", "vertical", "broad_jump", "three_cone")},
    "TE": {"positions": ("TE",), "features": (
        "combine_height", "combine_weight", "arm_length", "ten_yd_split",
        "forty", "vertical", "broad_jump", "three_cone")},
    "RB": {"positions": ("RB", "FB"), "features": (
        "combine_height", "combine_weight", "ten_yd_split",
        "forty", "vertical", "broad_jump", "short_shuttle")},
    "DL": {"positions": ("DE", "DT", "NT"), "features": (
        "combine_height", "combine_weight", "arm_length", "ten_yd_split",
        "vertical", "broad_jump", "three_cone", "short_shuttle")},
    "LB": {"positions": ("OLB", "ILB", "MLB"), "features": (
        "combine_height", "combine_weight", "arm_length", "ten_yd_split",
        "forty", "vertical", "broad_jump", "short_shuttle")},
    "DB": {"positions": ("CB", "DB", "FS", "SS"), "features": (
        "combine_height", "combine_weight", "arm_length", "ten_yd_split",
        "forty", "vertical", "broad_jump", "three_cone")},
}


def group_for(position):
    return next((name for name, rule in GROUPS.items() if position in rule["positions"]), None)


def number(value):
    """Missing, non-numeric and non-finite values stay missing; they never become zero."""
    if value is None or isinstance(value, bool) or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def fit_scaler(rows, features):
    """Mean and sample deviation from the reference pool only."""
    scaler = {}
    for name in features:
        values = [v for v in (number(row.get(name)) for row in rows) if v is not None]
        if len(values) < 2:
            continue
        mean = sum(values) / len(values)
        deviation = math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))
        if deviation > 0:
            scaler[name] = (mean, deviation)
    return scaler


def distance(first, second, scaler, feature_count):
    """Root mean squared standardized difference over shared features, or None."""
    squares = []
    for name, (_, deviation) in scaler.items():
        a, b = number(first.get(name)), number(second.get(name))
        if a is not None and b is not None:
            squares.append(((a - b) / deviation) ** 2)
    if len(squares) < max(MIN_SHARED_FEATURES, math.ceil(MIN_SHARED_FRACTION * feature_count - 1e-9)):
        return None
    return math.sqrt(sum(squares) / len(squares)), len(squares)


def nearest(target, pool, features, k=K, scaler=None):
    scaler = fit_scaler(pool, features) if scaler is None else scaler
    found = []
    for row in pool:
        if row["nfl_id"] == target["nfl_id"]:
            continue
        value = distance(target, row, scaler, len(features))
        if value is not None:
            found.append((value[0], row["nfl_id"], value[1], row))
    found.sort(key=lambda item: item[:2])
    return [{"distance": d, "shared_features": n, "row": row} for d, _, n, row in found[:k]]


def similar(target, pool, k=K):
    """Neighbours with a leave-one-measurement-out stability range."""
    group = group_for(target.get("nfl_position"))
    if group is None:
        return {"status": "unsupported_position", "group": None, "features": [], "pool_size": 0, "neighbors": []}
    features = GROUPS[group]["features"]
    others = [row for row in pool
              if group_for(row.get("nfl_position")) == group and row["nfl_id"] != target["nfl_id"]]
    base = {"group": group, "features": list(features), "pool_size": len(others), "neighbors": []}
    if len(others) < MIN_POOL:
        return {"status": "small_pool", **base}
    scaler = fit_scaler(others, features)
    matches = nearest(target, others, features, k, scaler)
    if len(matches) < k:
        return {"status": "insufficient_measurements", **base}
    usable = [name for name in scaler if number(target.get(name)) is not None]
    reruns = []
    for dropped in usable:
        reduced = {name: value for name, value in scaler.items() if name != dropped}
        reruns.append({"scaler": reduced, "ids": {
            match["row"]["nfl_id"] for match in nearest(target, others, reduced, k, reduced)}})
    for match in matches:
        row, values, kept = match["row"], [match["distance"]], 0
        for rerun in reruns:
            value = distance(target, row, rerun["scaler"], len(rerun["scaler"]))
            if value is not None:
                values.append(value[0])
            kept += row["nfl_id"] in rerun["ids"]
        base["neighbors"].append({
            "nfl_id": row["nfl_id"], "display_name": row["display_name"],
            "nfl_position": row["nfl_position"], "draft_year": row["draft_year"],
            "distance": match["distance"], "distance_low": min(values), "distance_high": max(values),
            "shared_features": match["shared_features"],
            "stability": kept / len(reruns),
        })
    return {"status": "ok", **base}
