"""Slow-storm scenario weights (spec: 'Scenario set and weightings').

Within each direction, a fraction lam of the fastest scenario's (speed 25) mass
moves to the slowest (speed 05): p = (1+lam)/n, 1/n, 1/n, (1-lam)/n.
"""
import pandas as pd

from slow_paths import short_name

SLOW_SPEED, FAST_SPEED = "05", "25"


def parse_scenario(name: str) -> tuple:
    direction, category, speed = short_name(name).split("_")
    return direction, category, speed


def slow_shift_weights(scenarios: list, lam: float) -> pd.Series:
    if not 0.0 <= lam <= 1.0:
        raise ValueError(f"lambda must be in [0, 1], got {lam}")
    names = [short_name(s) for s in scenarios]
    speeds_by_dir = {}
    for n in names:
        d, _, sp = parse_scenario(n)
        speeds_by_dir.setdefault(d, []).append(sp)
    for d, speeds in speeds_by_dir.items():
        if speeds.count(SLOW_SPEED) != 1 or speeds.count(FAST_SPEED) != 1:
            raise ValueError(f"direction {d!r} needs exactly one speed-{SLOW_SPEED} "
                             f"and one speed-{FAST_SPEED} scenario, got {speeds}")
    base = 1.0 / len(names)
    weights = {}
    for n in names:
        sp = parse_scenario(n)[2]
        if sp == SLOW_SPEED:
            weights[n] = base * (1 + lam)
        elif sp == FAST_SPEED:
            weights[n] = base * (1 - lam)
        else:
            weights[n] = base
    return pd.Series(weights)


def weighted_loss(vector: pd.Series, weights: pd.Series) -> float:
    """sum_k p_k L(x, k); `vector` is indexed by scenario short name."""
    return float((vector[weights.index].astype(float) * weights).sum())
