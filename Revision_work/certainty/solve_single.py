"""Step 2: the certain planner's decision x_k(I) for each scenario k and budget I.

Putting all probability on scenario k is the single-scenario model built from
input1 with only column k, which is the same model Bounds.ipynb solves for the
wait-and-see bound. Each (k, I) is solved in two phases:
  1. minimize load shed -> L_in and the raw (Gurobi-default) decision;
  2. tie-break: hold load shed at the phase-1 value and minimize hardening
     spend -> the primary decision, a plan that spends nothing on scenarios the
     planner believes cannot happen.
"""
import time
from pathlib import Path

from common import (REPO_ROOT, append_row, apply_solver_params, read_rows,  # noqa: F401
                    short_name, single_scenario_input1)
from env_check import check_environment

TIE_BREAK_REL_TOL = 1e-6


def solve_all(model_params: dict, scenario_cols: list, budgets: list, out_dir: Path):
    check_environment()
    from gurobipy import GRB
    from main_model import two_stage_model

    solves_dir = out_dir / "solves"
    solves_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "solve_results.csv"
    existing = read_rows(csv_path)
    done = set() if existing.empty else set(zip(existing["scenario"], existing["budget"]))

    for col in scenario_cols:
        name = short_name(col)
        # ascending budgets: each solution stays feasible for the next budget
        pending = [b for b in sorted(budgets) if (name, b) not in done]
        if not pending:
            continue

        params = dict(model_params)
        params["input1"] = single_scenario_input1(model_params["input1"], col)
        m = two_stage_model(params)
        gm = m.model
        apply_solver_params(gm, model_params)

        # Built explicitly: gm.getObjective() drops the objective's constant
        # (total load), which would make the tie-break cap vacuous.
        loss_expr = m.input1["load"].sum() - m.s.sum("*", "*") / m.n_scenarios
        cost_expr = m.fc * m.y.sum() + m.coarse * m.vc * m.x.sum()
        subs = list(m.unique_substations)

        for budget in pending:
            tag = f"{name}_{budget}M"
            m.budget_ref.rhs = budget * 1e6

            # Phase 1: minimize load shed
            gm.setObjective(loss_expr, GRB.MINIMIZE)
            gm.setParam("LogFile", str(solves_dir / f"{tag}_phase1.log"))
            t0 = time.time()
            gm.optimize()
            t_phase1 = time.time() - t0
            if gm.SolCount == 0:
                raise RuntimeError(f"{tag}: phase 1 found no solution (status {gm.Status})")
            L_in = gm.ObjVal
            assert abs(loss_expr.getValue() - L_in) <= 1e-6 * max(1.0, abs(L_in)), \
                f"{tag}: loss expression {loss_expr.getValue()} != objective {L_in}"
            phase1 = {"phase1_time_s": t_phase1, "phase1_gap": gm.MIPGap, "phase1_status": gm.Status}
            x_raw = {s: m.x[s].X for s in subs}
            spend_raw = cost_expr.getValue()
            gm.write(str(solves_dir / f"{tag}_raw.sol"))

            # Phase 2: minimum-spend tie-break at the phase-1 load shed
            all_vars = gm.getVars()
            gm.setAttr("Start", all_vars, gm.getAttr("X", all_vars))
            cap = gm.addConstr(loss_expr <= L_in + TIE_BREAK_REL_TOL * max(1.0, abs(L_in)),
                               name="tie_break_cap")
            gm.setObjective(cost_expr, GRB.MINIMIZE)
            gm.setParam("LogFile", str(solves_dir / f"{tag}_phase2.log"))
            t0 = time.time()
            gm.optimize()
            t_phase2 = time.time() - t0
            if gm.SolCount == 0:
                raise RuntimeError(f"{tag}: phase 2 found no solution (status {gm.Status})")
            L_in_tb = loss_expr.getValue()
            assert L_in_tb <= L_in + TIE_BREAK_REL_TOL * max(1.0, abs(L_in)) + 1e-4, \
                f"{tag}: tie-break increased load shed ({L_in_tb} > {L_in})"
            x_tb = {s: m.x[s].X for s in subs}
            spend_tb = cost_expr.getValue()
            phase2 = {"phase2_time_s": t_phase2, "phase2_gap": gm.MIPGap, "phase2_status": gm.Status}
            gm.write(str(solves_dir / f"{tag}_solution.sol"))

            gm.remove(cap)
            gm.setObjective(loss_expr, GRB.MINIMIZE)
            gm.update()

            row = {
                "scenario": name,
                "scenario_col": col,
                "budget": budget,
                "L_in": L_in,
                "L_in_tb": L_in_tb,
                **phase1,
                **phase2,
                "spend_raw": spend_raw,
                "spend_tb": spend_tb,
                "n_hardened_raw": sum(round(v) > 0 for v in x_raw.values()),
                "n_hardened_tb": sum(round(v) > 0 for v in x_tb.values()),
            }
            row.update({f"x_raw__{s}": x_raw[s] for s in subs})
            row.update({f"x_tb__{s}": x_tb[s] for s in subs})
            append_row(csv_path, row)
            print(f"[solve] {tag}: L_in={L_in:.4f} spend raw/tb={spend_raw / 1e6:.2f}/{spend_tb / 1e6:.2f}M "
                  f"t={t_phase1:.0f}+{t_phase2:.0f}s", flush=True)
        gm.dispose()

    return read_rows(csv_path)
