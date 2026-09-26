"""Step 3: evaluate each certain plan x_k on all 16 true MEOW scenarios.

Fix-and-resolve on the full 16-scenario model, as in
vsc/evaluate_decorrelated.py. One solve per plan gives L_SO(x_k) and the full
row L(x_k, k') of the cross-performance matrix from the `s` variables.
"""
import time
from pathlib import Path

import pandas as pd

from common import append_row, apply_solver_params, read_rows, short_name
from env_check import check_environment

VARIANTS = ("tb", "raw")


def evaluate_all(model_params: dict, solve_df: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    check_environment()
    from main_model import two_stage_model

    logs_dir = out_dir / "eval_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "eval_results.csv"
    existing = read_rows(csv_path)
    results = {} if existing.empty else {
        (r["scenario"], r["budget"], r["variant"]): r for _, r in existing.iterrows()}

    m = two_stage_model(model_params)
    gm = m.model
    apply_solver_params(gm, model_params)
    subs = list(m.unique_substations)
    scen_names = [short_name(c) for c in m.filter_col]
    load = m.input1["load"].values

    for _, rec in solve_df.iterrows():
        name, budget = rec["scenario"], rec["budget"]
        fixed = {v: {s: round(rec[f"x_{v}__{s}"]) for s in subs} for v in VARIANTS}

        for variant in VARIANTS:
            key = (name, budget, variant)
            if key in results:
                continue

            # The raw plan often equals the tie-broken one: reuse its evaluation.
            if variant == "raw" and fixed["raw"] == fixed["tb"]:
                row = dict(results[(name, budget, "tb")])
                row.update({"variant": "raw", "reused_from_tb": True})
                append_row(csv_path, row)
                results[key] = row
                continue

            m.budget_ref.rhs = budget * 1e6
            temp = gm.addConstrs(m.x[s] == fixed[variant][s] for s in subs)
            gm.setParam("LogFile", str(logs_dir / f"{name}_{budget}M_{variant}.log"))
            t0 = time.time()
            gm.optimize()
            t_eval = time.time() - t0
            if gm.SolCount == 0:
                raise RuntimeError(f"eval {key}: no solution (status {gm.Status})")

            shed = [sum(load[i] - m.s[i, k].X for i in range(m.n_buses)) for k in range(m.n_scenarios)]
            row = {
                "scenario": name,
                "budget": budget,
                "variant": variant,
                "L_SO_xk": gm.ObjVal,
                "worst_case_L_xk": max(shed),
                "eval_time_s": t_eval,
                "eval_gap": gm.MIPGap,
                "eval_status": gm.Status,
                "reused_from_tb": False,
            }
            row.update({f"L__{k}": v for k, v in zip(scen_names, shed)})
            append_row(csv_path, row)
            results[key] = row
            gm.remove(temp)
            gm.update()
            print(f"[eval] {name}_{budget}M_{variant}: L_SO(x_k)={row['L_SO_xk']:.4f} t={t_eval:.0f}s", flush=True)

    gm.dispose()
    return read_rows(csv_path)
