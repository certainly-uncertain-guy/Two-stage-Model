"""Shared helpers for the single-scenario certainty experiment.

Spec: Revision_work/single_scenario_certainty_experiment.md. Reuses the VSC
experiment's path/env/baseline helpers from Revision_work/vsc/. Module names in
this directory are chosen not to collide with vsc's (metrics.py, run_pilot.py),
because both directories end up on sys.path.
"""
import sys
from pathlib import Path

CERTAINTY_DIR = Path(__file__).resolve().parent
VSC_DIR = CERTAINTY_DIR.parent / "vsc"
sys.path.insert(0, str(VSC_DIR))

import csv

import pandas as pd

from paths import REPO_ROOT, SM16_OUTPUT_DIR, WAIT_AND_SEE_JSON  # noqa: E402,F401

sys.path.insert(0, str(REPO_ROOT))

CERTAINTY_RESULTS_DIR = REPO_ROOT / "certainty_results"
SCENARIO_PREFIX = "max_flood_level_"


def flood_columns(input1: pd.DataFrame) -> list:
    """Same rule as main_model.two_stage_model.filter_col."""
    return [c for c in input1.columns if c.startswith("max")]


def short_name(scenario_col: str) -> str:
    return scenario_col.replace(SCENARIO_PREFIX, "")


def scenario_subset_input1(input1: pd.DataFrame, scenario_cols: list) -> pd.DataFrame:
    """input1 with every flood column dropped except `scenario_cols`, which are
    appended last in the given order. The non-flood columns keep their positions,
    which matters because main_model indexes input1.values positionally (SubNum=2,
    gen min=6, gen max=7, load=8)."""
    out = input1.drop(columns=flood_columns(input1)).copy()
    for col in scenario_cols:
        out[col] = input1[col]
    return out


def single_scenario_input1(input1: pd.DataFrame, scenario_col: str) -> pd.DataFrame:
    return scenario_subset_input1(input1, [scenario_col])


def apply_solver_params(model, model_params: dict) -> None:
    model.setParam("LogToConsole", 0)
    model.setParam("MIPGap", model_params["mip_gap"])
    model.setParam("TimeLimit", model_params["time_limit"])
    model.setParam("Method", model_params["solver_method"])


def append_row(csv_path: Path, row: dict) -> None:
    """Append one result row, writing the header only when the file is new, so
    an interrupted run can be resumed."""
    write_header = not csv_path.exists()
    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def read_rows(csv_path: Path) -> pd.DataFrame:
    return pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame()
