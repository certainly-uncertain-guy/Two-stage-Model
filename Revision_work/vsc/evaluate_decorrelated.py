import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from paths import REPO_ROOT
from env_check import check_environment

sys.path.insert(0, str(REPO_ROOT))


def evaluate_all(model_params: dict, decorrelated_results: pd.DataFrame) -> pd.DataFrame:
    check_environment()
    from main_model import two_stage_model

    base_model = two_stage_model(model_params)
    base_model.model.setParam("LogToConsole", 0)
    base_model.model.setParam("MIPGap", model_params["mip_gap"])
    base_model.model.setParam("TimeLimit", model_params["time_limit"])
    base_model.model.setParam("Method", model_params["solver_method"])

    sub_ids = list(base_model.unique_substations)
    x_cols = [f"x_IND__{sub}" for sub in sub_ids]

    rows = []
    for _, rec in decorrelated_results.iterrows():
        budget = rec["budget"]
        base_model.budget_ref.rhs = budget * 1e6

        x_fixed = {sub: round(rec[f"x_IND__{sub}"]) for sub in sub_ids}
        temp = base_model.model.addConstrs(base_model.x[i] == x_fixed[i] for i in sub_ids)
        base_model.model.optimize()

        input1_load = base_model.input1["load"].values
        worst_case = max(
            sum(input1_load[i] - base_model.s[i, k].X for i in range(base_model.n_buses))
            for k in range(base_model.n_scenarios)
        )

        rows.append({
            "replication": rec["replication"],
            "budget": budget,
            "L_SO_xind": base_model.model.ObjVal,
            "worst_case_L_xind": worst_case,
        })
        base_model.model.remove(temp)

    return pd.DataFrame(rows)
