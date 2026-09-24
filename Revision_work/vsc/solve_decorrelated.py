import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import csv
import time

import pandas as pd

from paths import REPO_ROOT
from env_check import check_environment
from decorrelate import build_decorrelated_flood_df

sys.path.insert(0, str(REPO_ROOT))


def solve_one_replication(model_params: dict, seed: int, budget_vector: list, out_dir: Path) -> pd.DataFrame:
    check_environment()
    from main_model import two_stage_model

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "solve_decorrelated_results.csv"

    filter_col = [c for c in model_params["input1"].columns if c.startswith("max")]
    input1_no_flood = model_params["input1"].drop(columns=filter_col)
    decorrelated = build_decorrelated_flood_df(model_params["input1"], filter_col, seed=seed)

    rep_params = dict(model_params)
    rep_params["input1"] = pd.concat([input1_no_flood, decorrelated[filter_col]], axis=1)

    base_model = two_stage_model(rep_params)
    base_model.model.setParam("LogToConsole", 0)
    base_model.model.setParam("MIPGap", model_params["mip_gap"])
    base_model.model.setParam("TimeLimit", model_params["time_limit"])
    base_model.model.setParam("Method", model_params["solver_method"])

    sub_ids = list(base_model.unique_substations)
    rows = []
    write_header = not csv_path.exists()

    for budget in budget_vector:
        base_model.budget_ref.rhs = budget * 1e6
        t0 = time.time()
        base_model.model.optimize()
        solve_time = time.time() - t0

        base_model.model.write(str(out_dir / f"rep{seed}_{budget}M_solution.sol"))

        row = {
            "replication": seed,
            "budget": budget,
            "solve_time_s": solve_time,
            "mip_gap": base_model.model.MIPGap,
            "status": base_model.model.Status,
            "L_IND_in": base_model.model.ObjVal,
        }
        for sub_id in sub_ids:
            row[f"x_IND__{sub_id}"] = base_model.x[sub_id].X

        rows.append(row)
        with open(csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            if write_header:
                writer.writeheader()
                write_header = False
            writer.writerow(row)

    return pd.DataFrame(rows)
