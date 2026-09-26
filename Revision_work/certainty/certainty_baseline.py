"""Step 1: baseline curves (L*_SO, x_SO, L_SO(x_bar), L*_WS) via vsc.baseline,
cached per results directory.

L*_SO is taken from the original Gurobi logs in output/sm_16/ rather than the
2-decimal stochastic_solution.csv, together with each solve's final gap: the
$10M and $20M baseline solves hit the 6 h limit (gaps 1.8% and 4.7%), so L*_SO
is only an upper bound there.
"""
from pathlib import Path

import pandas as pd

from certainty_metrics import parse_gurobi_log
from common import SM16_OUTPUT_DIR


def get_baseline(model_params: dict, budgets: list, cache_path: Path) -> pd.DataFrame:
    cached = pd.read_csv(cache_path) if cache_path.exists() else pd.DataFrame(columns=["budget"])
    missing = sorted(set(budgets) - set(cached["budget"]))

    if missing:
        from baseline import reproduce_baseline

        df = reproduce_baseline(model_params, missing)
        exact = [parse_gurobi_log(SM16_OUTPUT_DIR / f"{b}M") for b in df["budget"]]
        df["L_SO_star_csv"] = df["L_SO_star"]
        df["L_SO_star"] = [obj for obj, _ in exact]
        df["L_SO_star_gap"] = [gap for _, gap in exact]
        cached = pd.concat([cached, df], ignore_index=True) if len(cached) else df
        cached = cached.sort_values("budget").reset_index(drop=True)
        cached.to_csv(cache_path, index=False)

    return cached[cached["budget"].isin(budgets)].reset_index(drop=True)
