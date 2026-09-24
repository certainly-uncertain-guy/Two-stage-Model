import pandas as pd


def _selected(x: dict) -> set:
    return {sub for sub, height in x.items() if round(height) > 0}


def jaccard_index(x_so: dict, x_ind: dict) -> float:
    a, b = _selected(x_so), _selected(x_ind)
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def mean_abs_height_diff(x_so: dict, x_ind: dict) -> float:
    common = _selected(x_so) & _selected(x_ind)
    if not common:
        return float("nan")
    diffs = [abs(x_so[s] - x_ind[s]) for s in common]
    return sum(diffs) / len(diffs)


def budget_allocation(x: dict) -> dict:
    selected = _selected(x)
    heights = [x[s] for s in selected]
    return {
        "n_hardened": len(selected),
        "mean_height": (sum(heights) / len(heights)) if heights else 0.0,
    }


def selection_frequency(x_ind_by_rep: dict) -> pd.Series:
    all_subs = sorted({sub for x in x_ind_by_rep.values() for sub in x})
    n_reps = len(x_ind_by_rep)
    counts = {sub: 0 for sub in all_subs}
    for x in x_ind_by_rep.values():
        for sub in _selected(x):
            counts[sub] += 1
    return pd.Series({sub: c / n_reps for sub, c in counts.items()})
