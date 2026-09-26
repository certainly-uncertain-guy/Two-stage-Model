"""Orchestrator for the slow-storm sensitivity experiment.

    /opt/miniconda3/bin/python Revision_work/slow_storm/run_slow_storm.py pilot
    /opt/miniconda3/bin/python Revision_work/slow_storm/run_slow_storm.py full [BUDGETS]
    /opt/miniconda3/bin/python Revision_work/slow_storm/run_slow_storm.py report {pilot|full}

Fixed-plan vectors (SO/RO/MV, all budgets) are shared by both modes. Only the
re-optimized SLOW plan differs: pilot re-solves $20M/$40M/$60M, full all 9
(or a comma-separated subset, e.g. `full 0,40,50,60,70,80`; rerun later to add the rest).
Every solve is appended as it finishes, so rerunning resumes.
"""
import sys
import time

import pandas as pd

from slow_paths import CERTAINTY_RESULTS_DIR, SLOW_RESULTS_DIR, flood_columns, read_rows

ALL_BUDGETS = [0, 10, 20, 30, 40, 50, 60, 70, 80]
PILOT_SLOW_BUDGETS = [20, 40, 60]


def _slow_plans(slow_df: pd.DataFrame) -> dict:
    subs = [c[len("x__"):] for c in slow_df.columns if c.startswith("x__")]
    return {int(r["budget"]): {s: float(r[f"x__{s}"]) for s in subs} for _, r in slow_df.iterrows()}


def run(mode: str, slow_budgets: list = None):
    from baseline import load_config
    from certainty_baseline import get_baseline
    from slow_evaluate import evaluate_plans
    from slow_plans import mv_plans, ro_plans, so_plans
    from slow_report import build_report
    from slow_solve import solve_weighted
    from storm_weights import slow_shift_weights

    out_dir = SLOW_RESULTS_DIR / mode
    out_dir.mkdir(parents=True, exist_ok=True)
    model_params = load_config(time_limit_override=None)  # config.yaml's 6 h

    t0 = time.time()
    baseline_df = get_baseline(model_params, ALL_BUDGETS, CERTAINTY_RESULTS_DIR / "baseline.csv")
    plans = {"SO": so_plans(baseline_df),
             "RO": ro_plans(model_params, ALL_BUDGETS, SLOW_RESULTS_DIR / "ro_plans.json"),
             "MV": mv_plans(model_params, ALL_BUDGETS, SLOW_RESULTS_DIR / "mv_plans.json")}
    fixed = evaluate_plans(model_params, plans, SLOW_RESULTS_DIR / "fixed_plan_vectors.csv")
    print(f"[{mode}] fixed-plan vectors ready ({time.time() - t0:.0f}s)", flush=True)

    weights = slow_shift_weights(flood_columns(model_params["input1"]), 1.0)
    budgets = slow_budgets or (PILOT_SLOW_BUDGETS if mode == "pilot" else ALL_BUDGETS)
    t0 = time.time()
    slow_df = solve_weighted(model_params, weights, budgets, plans["SO"], out_dir)
    print(f"[{mode}] slow re-solves done ({time.time() - t0:.0f}s)", flush=True)

    slow_vec = evaluate_plans(model_params, {"SLOW": _slow_plans(slow_df)}, out_dir / "slow_plan_vectors.csv")
    vectors = pd.concat([fixed, slow_vec], ignore_index=True)
    s, checks = build_report(out_dir, model_params, baseline_df, vectors, slow_df)
    print(s.to_string(index=False))
    print(f"[{mode}] validation: {int(checks['passed'].sum())}/{len(checks)} checks passed", flush=True)


def report_only(mode: str):
    from baseline import load_config
    from slow_report import build_report

    out_dir = SLOW_RESULTS_DIR / mode
    model_params = load_config(time_limit_override=None)
    baseline_df = pd.read_csv(CERTAINTY_RESULTS_DIR / "baseline.csv")
    slow_df = read_rows(out_dir / "slow_solves.csv")
    vectors = pd.concat([read_rows(SLOW_RESULTS_DIR / "fixed_plan_vectors.csv"),
                         read_rows(out_dir / "slow_plan_vectors.csv")], ignore_index=True)
    s, checks = build_report(out_dir, model_params, baseline_df, vectors, slow_df)
    print(s.to_string(index=False))
    print(f"[report {mode}] validation: {int(checks['passed'].sum())}/{len(checks)} checks passed")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 1 and args[0] in ("pilot", "full"):
        run(args[0])
    elif len(args) == 2 and args[0] == "full":
        run("full", [int(b) for b in args[1].split(",")])
    elif len(args) == 2 and args[0] == "report" and args[1] in ("pilot", "full"):
        report_only(args[1])
    else:
        sys.exit(__doc__)
