"""First-stage plans to evaluate: SO (from certainty_results/baseline.csv), RO
(from output/rm_16/*.sol) and MV (EV solve). RO and MV are cached as JSON."""
import json
from pathlib import Path

import pandas as pd

from env_check import check_environment
from slow_paths import RM16_OUTPUT_DIR


def so_plans(baseline_df: pd.DataFrame) -> dict:
    subs = [c[len("x_SO__"):] for c in baseline_df.columns if c.startswith("x_SO__")]
    return {int(r["budget"]): {s: float(r[f"x_SO__{s}"]) for s in subs} for _, r in baseline_df.iterrows()}


def _cached(cache_path: Path, budgets: list, compute) -> dict:
    cache = {}
    if cache_path.exists():
        cache = {int(b): plan for b, plan in json.loads(cache_path.read_text()).items()}
    missing = [b for b in budgets if b not in cache]
    if missing:
        cache.update(compute(missing))
        cache_path.write_text(json.dumps({str(b): cache[b] for b in sorted(cache)}, indent=1))
    return {b: cache[b] for b in budgets}


def ro_plans(model_params: dict, budgets: list, cache_path: Path) -> dict:
    def compute(missing):
        check_environment()
        from main_model import two_stage_model

        params = dict(model_params)
        params["robust_flag"] = True  # .sol files carry tau/tau_scenario
        m = two_stage_model(params)
        m.model.setParam("LogToConsole", 0)
        m.model.update()
        out = {}
        for b in missing:
            m.model.read(str(RM16_OUTPUT_DIR / f"{b}M_solution.sol"))
            m.model.update()
            out[b] = {str(s): m.model.getVarByName(f"x[{s}]").Start for s in m.unique_substations}
        m.model.dispose()
        return out

    return _cached(cache_path, budgets, compute)


def mv_plans(model_params: dict, budgets: list, cache_path: Path) -> dict:
    def compute(missing):
        check_environment()
        from baseline import mean_value_solutions

        sols = mean_value_solutions(model_params, missing)
        return {b: {str(s): float(v) for s, v in sols[b].items()} for b in missing}

    return _cached(cache_path, budgets, compute)
