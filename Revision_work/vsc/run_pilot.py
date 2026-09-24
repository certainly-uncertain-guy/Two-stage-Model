import time
import pandas as pd

from paths import VSC_RESULTS_DIR
from baseline import load_config, reproduce_baseline
from solve_decorrelated import solve_one_replication
from evaluate_decorrelated import evaluate_all
from metrics import compute_metrics, summarize

PILOT_BUDGETS = [20, 40, 60]
PILOT_SEEDS = [1, 2]


def run_pilot():
    out_dir = VSC_RESULTS_DIR / "pilot"
    out_dir.mkdir(parents=True, exist_ok=True)

    model_params = load_config()
    baseline_df = reproduce_baseline(model_params, PILOT_BUDGETS)
    baseline_df.to_csv(out_dir / "baseline.csv", index=False)

    all_solve, all_eval = [], []
    for seed in PILOT_SEEDS:
        t0 = time.time()
        solve_df = solve_one_replication(model_params, seed, PILOT_BUDGETS, out_dir / "solves")
        t_solve = time.time() - t0

        t0 = time.time()
        eval_df = evaluate_all(model_params, solve_df)
        t_eval = time.time() - t0

        print(f"replication {seed}: solve={t_solve:.1f}s eval={t_eval:.1f}s "
              f"(eval/solve ratio={t_eval / t_solve:.2f})")

        all_solve.append(solve_df)
        all_eval.append(eval_df)

    solve_df = pd.concat(all_solve, ignore_index=True)
    eval_df = pd.concat(all_eval, ignore_index=True).merge(
        solve_df[["replication", "budget", "L_IND_in"]], on=["replication", "budget"]
    )
    metrics_df = compute_metrics(baseline_df, eval_df, model_params["mip_gap"])
    metrics_df.to_csv(out_dir / "pilot_results.csv", index=False)
    print(summarize(metrics_df))


if __name__ == "__main__":
    run_pilot()
