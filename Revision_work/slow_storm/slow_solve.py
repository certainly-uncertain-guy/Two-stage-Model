"""Re-optimize the SO plan under non-uniform scenario weights (spec: x_slow).

Zero-weight scenarios are dropped from input1 so the model only carries the
scenarios that matter, and the objective is replaced by the explicitly built
weighted expected load shed: load.sum() - sum_k p_k sum_i s[i,k].
"""
import time
from pathlib import Path

import pandas as pd

from env_check import check_environment
from slow_paths import (append_row, apply_solver_params, flood_columns, read_rows,
                        scenario_subset_input1, short_name)


def solve_weighted(model_params: dict, weights: pd.Series, budgets: list, warm_plans: dict,
                   out_dir: Path) -> pd.DataFrame:
    solves_dir = out_dir / "solves"
    solves_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "slow_solves.csv"
    existing = read_rows(csv_path)
    done = set() if existing.empty else set(existing["budget"])
    pending = [b for b in sorted(budgets) if b not in done]
    if not pending:
        return existing

    check_environment()
    import gurobipy as gp
    from gurobipy import GRB
    from main_model import two_stage_model

    keep = [c for c in flood_columns(model_params["input1"]) if weights[short_name(c)] > 0]
    params = dict(model_params)
    params["input1"] = scenario_subset_input1(model_params["input1"], keep)
    m = two_stage_model(params)
    gm = m.model
    apply_solver_params(gm, model_params)

    p = [float(weights[short_name(c)]) for c in m.filter_col]
    total = sum(p)
    p = [v / total for v in p]
    loss_expr = m.input1["load"].sum() - gp.quicksum(
        p[k] * m.s[i, k] for k in range(m.n_scenarios) for i in range(m.n_buses))
    gm.setObjective(loss_expr, GRB.MINIMIZE)
    cost_expr = m.fc * m.y.sum() + m.coarse * m.vc * m.x.sum()
    key = {str(s): s for s in m.unique_substations}
    print(f"[slow] model over {m.n_scenarios} scenarios, weights {dict(zip(map(short_name, m.filter_col), p))}",
          flush=True)

    for budget in pending:
        m.budget_ref.rhs = budget * 1e6
        if budget in warm_plans:
            for s, v in warm_plans[budget].items():
                m.x[key[s]].Start = round(v)
                m.y[key[s]].Start = 1 if round(v) > 0 else 0
        gm.setParam("LogFile", str(solves_dir / f"slow_{budget}M.log"))
        t0 = time.time()
        gm.optimize()
        t_solve = time.time() - t0
        if gm.SolCount == 0:
            raise RuntimeError(f"slow ${budget}M: no solution (status {gm.Status})")
        assert abs(loss_expr.getValue() - gm.ObjVal) <= 1e-6 * max(1.0, abs(gm.ObjVal)), \
            f"slow ${budget}M: loss expression {loss_expr.getValue()} != objective {gm.ObjVal}"
        gm.write(str(solves_dir / f"slow_{budget}M_solution.sol"))
        row = {"budget": budget, "L_star_slow_solver": gm.ObjVal, "bound": gm.ObjBound,
               "gap": gm.MIPGap, "status": gm.Status, "solve_time_s": t_solve,
               "spend": cost_expr.getValue(),
               "n_hardened": sum(round(m.x[s].X) > 0 for s in m.unique_substations)}
        row.update({f"x__{s}": m.x[s].X for s in m.unique_substations})
        append_row(csv_path, row)
        print(f"[slow] ${budget}M: L*_slow={gm.ObjVal:.4f} gap={100 * gm.MIPGap:.2f}% t={t_solve:.0f}s",
              flush=True)

    gm.dispose()
    return read_rows(csv_path)
