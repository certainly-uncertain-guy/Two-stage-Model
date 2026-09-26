import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import json

import numpy as np
import pandas as pd
import yaml

from paths import REPO_ROOT, SM16_OUTPUT_DIR, WAIT_AND_SEE_JSON, input_dir_str, INPUT_DIR_16
from env_check import check_environment

sys.path.insert(0, str(REPO_ROOT))


def load_config(time_limit_override: int | None = 7200) -> dict:
    check_environment()
    from utils import prepare_input

    with open(REPO_ROOT / "config.yaml") as f:
        model_params = yaml.safe_load(f)
    model_params["path_to_input"] = input_dir_str(INPUT_DIR_16)
    model_params["input1"], model_params["input2"] = prepare_input(model_params["path_to_input"])

    # VSC-experiment-only override: config.yaml's time_limit (21600s/6h) was
    # calibrated for the original correlated MEOW scenarios. Decorrelated
    # scenarios are far harder to solve to the same 0.5% mip_gap (confirmed:
    # a single mid-range budget didn't reach it even after the full 6h), so
    # per-solve time is capped at 2h here instead, per explicit user
    # instruction. config.yaml itself is left untouched so other notebooks
    # (stochastic_model.ipynb, robust_model.ipynb, etc.) keep reproducing the
    # manuscript's original settings.
    # Other experiments (e.g. Revision_work/certainty/) pass None to keep
    # config.yaml's time_limit unchanged.
    if time_limit_override is not None:
        model_params["time_limit"] = time_limit_override
    return model_params


def _worst_case_load_shed_from_start(base_model) -> float:
    """max over scenarios k of sum_j (D_j - s[j,k]), read from a .sol-populated
    (but not re-optimized) model via .Start rather than .X."""
    input1_load = base_model.input1["load"].values
    per_scenario = []
    for k in range(base_model.n_scenarios):
        shed = sum(
            input1_load[i] - base_model.s[i, k].Start
            for i in range(base_model.n_buses)
        )
        per_scenario.append(shed)
    return max(per_scenario)


def reproduce_baseline(model_params: dict, budget_vector: list) -> pd.DataFrame:
    from main_model import two_stage_model

    base_model = two_stage_model(model_params)
    base_model.model.setParam("LogToConsole", 0)
    base_model.model.update()

    # --- x_SO and worst_case_L_SO via .sol reload (analysis.py's pattern) ---
    rows = []
    sub_ids = list(base_model.unique_substations)
    for budget in budget_vector:
        sol_path = SM16_OUTPUT_DIR / f"{budget}M_solution.sol"
        base_model.model.read(str(sol_path))
        base_model.model.update()
        row = {"budget": budget}
        for sub_id in sub_ids:
            row[f"x_SO__{sub_id}"] = base_model.model.getVarByName(f"x[{sub_id}]").Start
        row["worst_case_L_SO"] = _worst_case_load_shed_from_start(base_model)
        rows.append(row)

    df = pd.DataFrame(rows).set_index("budget")

    # L*_SO(I): reuse the manuscript-reported values already aggregated in
    # output/sm_16/stochastic_solution.csv (produced by the same .sol files).
    # NOTE: the CSV carries a real header row ("index,budget") where the
    # "budget" column actually holds the objective (unserved-load) values and
    # the "index" column holds the budgets -- read with the default header
    # (not header=None) so index_col=0 lines up on budget.
    ss = pd.read_csv(SM16_OUTPUT_DIR / "stochastic_solution.csv", index_col=0).iloc[:, 0]
    df["L_SO_star"] = [ss.loc[b] for b in df.index]

    # --- L*_WS(I) from the cached wait-and-see dict ---
    with open(WAIT_AND_SEE_JSON) as f:
        was_dict = json.load(f)
    df["L_WS_star"] = [np.mean(list(was_dict[str(b)].values())) for b in df.index]

    # --- L_SO(x_bar): mean-value solution, evaluated on the original scenarios ---
    df["L_SO_xbar"] = _mean_value_bound(model_params, budget_vector)

    return df.reset_index()


def mean_value_solutions(model_params: dict, budget_vector: list) -> dict:
    """EV-model decisions per budget: {budget: {substation: x}} (Bounds.ipynb's
    mean-value pipeline, first half)."""
    from main_model import two_stage_model

    flood_df = model_params["input1"][model_params["input1"].columns[model_params["input1"].columns.str.startswith("max")]]
    input1_no_flood = model_params["input1"].drop(columns=flood_df.columns)

    ev_params = dict(model_params)
    ev_input1 = input1_no_flood.copy()
    ev_input1["max_mean_value_solution"] = np.ceil(flood_df.mean(axis=1))
    ev_params["input1"] = ev_input1

    mean_solution = {}
    for budget in budget_vector:
        ev_model = two_stage_model(ev_params)
        ev_model.model.setParam("LogToConsole", 0)
        ev_model.budget_ref.rhs = budget * 1e6
        ev_model.model.setParam("MIPGap", model_params["mip_gap"])
        ev_model.model.setParam("TimeLimit", model_params["time_limit"])
        ev_model.model.setParam("Method", model_params["solver_method"])
        ev_model.model.optimize()
        mean_solution[budget] = {sub: ev_model.x[sub].X for sub in ev_model.x}
    return mean_solution


def _mean_value_bound(model_params: dict, budget_vector: list) -> list:
    """Reproduces Bounds.ipynb's mean-value pipeline: solve EV on the rounded
    mean scenario, then fix x to that solution and re-optimize on the full
    16-scenario model."""
    from main_model import two_stage_model

    mean_solution = mean_value_solutions(model_params, budget_vector)

    full_model = two_stage_model(model_params)
    full_model.model.setParam("LogToConsole", 0)
    bound = {}
    for budget in budget_vector:
        full_model.budget_ref.rhs = budget * 1e6
        temp = full_model.model.addConstrs(
            full_model.x[i] == round(mean_solution[budget][i]) for i in mean_solution[budget]
        )
        full_model.model.setParam("MIPGap", model_params["mip_gap"])
        full_model.model.setParam("TimeLimit", model_params["time_limit"])
        full_model.model.setParam("Method", model_params["solver_method"])
        full_model.model.optimize()
        bound[budget] = full_model.model.ObjVal
        full_model.model.remove(temp)

    return [bound[b] for b in budget_vector]
