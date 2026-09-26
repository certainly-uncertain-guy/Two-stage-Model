"""Orchestrator for the single-scenario certainty experiment.

    /opt/miniconda3/bin/python Revision_work/certainty/run_certainty.py pilot
    /opt/miniconda3/bin/python Revision_work/certainty/run_certainty.py full
    /opt/miniconda3/bin/python Revision_work/certainty/run_certainty.py report {pilot|full}

Every solve is appended to CSV as it finishes, so rerunning the same command
resumes where it stopped. Solves run sequentially: config.yaml does not set
Threads, so each solve uses all cores.
"""
import sys
import time

from common import CERTAINTY_RESULTS_DIR, flood_columns, read_rows, short_name

ALL_BUDGETS = [0, 10, 20, 30, 40, 50, 60, 70, 80]
PILOT_BUDGETS = [20, 40, 60]
# one scenario per storm direction, forward speed 10
PILOT_SCENARIOS = ["w_5_10", "wnw_5_10", "nw_5_10", "nnw_5_10"]


def _setup(mode: str):
    from baseline import load_config

    model_params = load_config(time_limit_override=None)  # keep config.yaml's 6 h
    all_cols = flood_columns(model_params["input1"])
    if mode == "pilot":
        cols = [c for c in all_cols if short_name(c) in PILOT_SCENARIOS]
        budgets, out_dir = PILOT_BUDGETS, CERTAINTY_RESULTS_DIR / "pilot"
    else:
        cols, budgets, out_dir = all_cols, ALL_BUDGETS, CERTAINTY_RESULTS_DIR / "full"
    out_dir.mkdir(parents=True, exist_ok=True)
    return model_params, cols, budgets, out_dir


def run(mode: str):
    from certainty_baseline import get_baseline
    from certainty_report import build_report
    from evaluate_certain import evaluate_all
    from solve_single import solve_all

    model_params, cols, budgets, out_dir = _setup(mode)
    print(f"[{mode}] {len(cols)} scenarios x {len(budgets)} budgets -> {out_dir}", flush=True)

    t0 = time.time()
    baseline_df = get_baseline(model_params, budgets, CERTAINTY_RESULTS_DIR / "baseline.csv")
    print(f"[{mode}] baseline ready ({time.time() - t0:.0f}s)", flush=True)

    t0 = time.time()
    solve_df = solve_all(model_params, cols, budgets, out_dir)
    print(f"[{mode}] solves done ({time.time() - t0:.0f}s)", flush=True)

    t0 = time.time()
    eval_df = evaluate_all(model_params, solve_df, out_dir)
    print(f"[{mode}] evaluations done ({time.time() - t0:.0f}s)", flush=True)

    _, summary, chain = build_report(out_dir, baseline_df, solve_df, eval_df, model_params["mip_gap"])
    print(summary.to_string(index=False))
    print(chain.to_string(index=False))


def report_only(mode: str):
    """Rebuild tables/figures from existing CSVs without solving anything."""
    import pandas as pd
    import yaml

    from certainty_report import build_report
    from common import REPO_ROOT

    out_dir = CERTAINTY_RESULTS_DIR / mode
    with open(REPO_ROOT / "config.yaml") as f:
        mip_gap = yaml.safe_load(f)["mip_gap"]
    baseline_df = pd.read_csv(CERTAINTY_RESULTS_DIR / "baseline.csv")
    solve_df = read_rows(out_dir / "solve_results.csv")
    eval_df = read_rows(out_dir / "eval_results.csv")
    baseline_df = baseline_df[baseline_df["budget"].isin(set(solve_df["budget"]))]
    _, summary, chain = build_report(out_dir, baseline_df, solve_df, eval_df, mip_gap)
    print(summary.to_string(index=False))
    print(chain.to_string(index=False))


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 1 and args[0] in ("pilot", "full"):
        run(args[0])
    elif len(args) == 2 and args[0] == "report" and args[1] in ("pilot", "full"):
        report_only(args[1])
    else:
        sys.exit(__doc__)
