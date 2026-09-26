"""Per-scenario load-shed vectors L(x, k) for fixed plans (spec: 'Key observation').

Fix x on the full 16-scenario model and re-optimize at MIPGap 1e-4, so each
scenario's entry (not only the uniform sum) is accurate enough to reweight.
"""
import time
from pathlib import Path

import pandas as pd

from env_check import check_environment
from slow_paths import append_row, apply_solver_params, read_rows, short_name

EVAL_MIP_GAP = 1e-4


def evaluate_plans(model_params: dict, plans: dict, out_csv: Path) -> pd.DataFrame:
    existing = read_rows(out_csv)
    done = set() if existing.empty else set(zip(existing["plan"], existing["budget"]))
    todo = [(p, b, x) for p, by_budget in plans.items() for b, x in sorted(by_budget.items())
            if (p, b) not in done]
    if not todo:
        return existing

    check_environment()
    from main_model import two_stage_model

    logs_dir = out_csv.parent / "eval_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    m = two_stage_model(model_params)
    gm = m.model
    apply_solver_params(gm, model_params)
    gm.setParam("MIPGap", EVAL_MIP_GAP)
    key = {str(s): s for s in m.unique_substations}
    names = [short_name(c) for c in m.filter_col]
    load = m.input1["load"].values

    for plan, budget, x in todo:
        m.budget_ref.rhs = budget * 1e6
        temp = gm.addConstrs(m.x[key[s]] == round(v) for s, v in x.items())
        gm.setParam("LogFile", str(logs_dir / f"{plan}_{budget}M.log"))
        t0 = time.time()
        gm.optimize()
        t_eval = time.time() - t0
        if gm.SolCount == 0:
            raise RuntimeError(f"{plan} ${budget}M: fixed plan has no feasible recourse (status {gm.Status})")
        shed = [sum(load[i] - m.s[i, k].X for i in range(m.n_buses)) for k in range(m.n_scenarios)]
        row = {"plan": plan, "budget": budget, "L_uniform": gm.ObjVal, "eval_time_s": t_eval,
               "eval_gap": gm.MIPGap, "eval_status": gm.Status}
        row.update({f"L__{n}": v for n, v in zip(names, shed)})
        append_row(out_csv, row)
        gm.remove(temp)
        gm.update()
        print(f"[eval] {plan}_{budget}M: uniform={row['L_uniform']:.4f} t={t_eval:.0f}s", flush=True)

    gm.dispose()
    return read_rows(out_csv)
