# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Research code (not a production application) accompanying the paper "Transmission Grid Resilience Planning Under Flood Uncertainty" (full text in [Manuscript/Two_stage_Models_for_Transmission_Grid_Resilience_Planning_to_Extreme_Flooding_Events.pdf](Manuscript/Two_stage_Models_for_Transmission_Grid_Resilience_Planning_to_Extreme_Flooding_Events.pdf)). It implements two-stage stochastic and robust MILP optimization models that couple hurricane flood predictions with a DC power flow model to recommend optimal substation hardening investments under flood uncertainty.

There is no build system, package manifest, linter, or test suite — the codebase is driven through Jupyter notebooks that call into a small set of shared Python modules.

## Running the models

Everything is run interactively via Jupyter notebooks; there are no CLI entry points.

- `stochastic_model.ipynb` — solves the two-stage stochastic formulation (`robust_flag: False`) over a swept `budget_vector`, writing Gurobi logs and `.sol` files to `output/sm_<n_scenario>/`.
- `robust_model.ipynb` — same flow with `robust_flag = True` (worst-case/min-max objective), writing to `output/rm_<n_scenario>/` (or `coarse_rm_<n_scenario>/`).
- `reduced_scenario.ipynb` — builds a non-dominated subset of flood scenarios (dominance filtering over `max_flood_*` columns) before running the robust model on the reduced scenario set.
- `fixed_reduced_grid/scenario_constructor.ipynb` — constructs the `Final_Input1.csv` / `Final_Input2.csv` scenario datasets consumed by the models.

Common pattern in every "run" notebook:
1. Load `config.yaml` with `yaml.safe_load`/`yaml.load`.
2. Call `utils.prepare_input(path_to_input)` to load and per-unit-correct `Final_Input1.csv` / `Final_Input2.csv`.
3. Instantiate `main_model.two_stage_model(model_params)`, which builds the full Gurobi model in its constructor.
4. Loop over a `budget_vector` (in $, e.g. `[0, 10e6, ...]`), mutate `base_model.budget_ref.rhs`, set Gurobi params (`MIPGap`, `TimeLimit`, `Method`) from `config.yaml`, call `.optimize()`, and write `.sol` / log files per budget into `output/<dir_name>/`.
5. Dump `model_params` (minus the loaded DataFrames) to `model_params.json` alongside the solutions for later reuse by `output_analysis/analysis.py`.

Requires a working Gurobi installation with a valid license (`gurobipy`); `solver_type`/`solver_method` in `config.yaml` are passed straight to Gurobi. `utils.py` also imports `pyomo` but it is unused (`main_model.py` uses `gurobipy` directly).

**Hardcoded paths**: several notebooks and `output_analysis/analysis.py` reference absolute paths from the original author's machine (e.g. `/Users/ashutoshshukla/Desktop/...`, or `os.path.dirname(os.getcwd()) + '/Data/fixed_reduced_grid/...'` implying a sibling `Data/` directory outside this repo). These need to be updated to point at this repo's `fixed_reduced_grid/<N>_Scenario/` and `output/` directories before re-running.

## Architecture

**`config.yaml`** — single source of truth for cost parameters (`fixed_cost`, `variable_cost`, `budget`, `mit_coarse`), model variant flags (`flexible_generation`, `robust_flag`), the optimization sense (`set_objective`), the power-flow `reference_bus`, and Gurobi solver settings (`mip_gap`, `time_limit`, `solver_type`, `solver_method`). Notebooks load this dict and then inject runtime-only keys (`input1`, `input2`, `path_to_input`, `path_to_output`) before passing it to `two_stage_model`.

**`utils.py`** — `prepare_input(path_str)` reads `Final_Input1.csv` (per-bus data: bus/substation IDs, coordinates, generation bounds, load, and one `max_flood_level_*` column per flood scenario) and `Final_Input2.csv` (per-branch data: `FROM_BUS`, `TO_BUS`, reactance `BR_X`, thermal limit `RATE_A`), re-indexes them, and converts generation/load/rate columns to per-unit (divide by 100).

**`main_model.py`** (`two_stage_model`) — the core MILP, built entirely in the constructor by calling a fixed sequence of methods:
- Stage-1 (hardening) decision variables: `y` (binary, harden substation or not) and `x` (integer, hardening level), one per unique substation, linked via `box_constraints` and priced via `budget_constraint` (`fixed_cost * y + variable_cost * mit_coarse * x <= budget`).
- Stage-2 (per-scenario operational) variables, indexed by bus × scenario: `z` (bus energized), `g` (generation), `s` (served load), `theta` (phase angle); and per-branch × scenario: `edge` (power flow), using a DC power-flow (DC-OPF) linearization with big-M constraints (`edge_constraints`) tied to a `reference_bus` (`phase_angle`).
- `linking_and_capacity_constraints` ties stage-1 hardening (`x`) to whether a bus survives flooding (`z`) via a linearized flood-threshold relationship, and bounds generation between min/max capacity (or via `alpha`, an optional per-bus/scenario "flexible generation" binary, when `flexible_generation: True`).
- `flow_balance_constraints` enforces nodal balance (`generation - load_shed = net flow`) using a node-arc incidence matrix built in `node_matrix`.
- Objective (`set_objective`) branches on `robust_flag`: when `True`, minimizes the worst-case unserved load `tau` across scenarios (`robust_constraints` epigraph formulation); when `False`, minimizes/maximizes the scenario-averaged unserved/served load per `set_objective` in the config.

**`fixed_reduced_grid/`** — input datasets, one subdirectory per scenario-set size (`8_Scenario`, `16_Scenario`, `48_Scenario`, `192_Scenario`), each holding a `Final_Input1.csv`/`Final_Input2.csv` pair in the format `prepare_input` expects. `modification_information/` documents how these were derived from the original grid data.

**`output/`** — one directory per model run, named `<sm|rm>_<n_scenario>` (stochastic vs. robust model). Each contains, per swept budget, a Gurobi log file and a `<budget>M_solution.sol`, plus `model_params.json` (the config used for that run) and aggregate result CSVs (`stochastic_solution.csv`, `robust_solution.csv`, `robust_decisions_stochastic_solutions.csv`).

**`output_analysis/`** — post-processing layer consumed after models finish solving:
- `analysis.py` (`analysis` class) reloads `model_params.json` for a given run, rebuilds the `two_stage_model` (needed to get variable objects), then loads each budget's `.sol` file into it via Gurobi's `model.read`/`getVarByName` to reconstruct hardening decisions (`x`) across the budget sweep into a DataFrame, filtering out substations never hardened.
- Notebooks (`Bounds`, `Discussion`, `Heuristic_Comparison`, `Optimal_budget`, `Robust_performance`, `VOLL_variation`, `Visualization`) consume `analysis.py` output plus the cached JSON dicts in `output_analysis/` and `output_analysis/voll_analysis/` to produce the figures checked into `Figures/` (referenced from the paper).

## Notes

- `README.md`, `Reproducibility_Report (Not for Review).docx`, and the paper in `Manuscript/` contain the paper-facing description of this codebase; consult them for the modeling background (flood correlation, VOLL, robust vs. stochastic framing) before making modeling changes.
- There is no automated test suite. The only way to validate a change to `main_model.py` is to re-run one of the model notebooks end-to-end (small scenario counts, e.g. `8_Scenario` or `16_Scenario`, solve fastest) and compare objective values / `.sol` output against `output/`.
