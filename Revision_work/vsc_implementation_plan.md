# Value of Spatial Correlation (VSC) Experiment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible pipeline that isolates the value of spatial correlation (VSC) in the NOAA MEOW flood scenarios by comparing the stochastic model (SO) on the original 16-scenario set against SO on a decorrelated (marginal-preserving, dependence-destroying) version of the same scenarios, decomposing VSS = VMV + VSC per the manuscript's Eq. (11), and producing the rebuttal deliverables.

**Architecture:** A set of small, reusable Python modules under `Revision_work/vsc/` (no new notebooks, per the spec's Instruction 3), each wrapping one step of the spec (baseline reproduction, decorrelated-scenario construction, SO solve on decorrelated scenarios, fix-and-resolve evaluation, metrics, decision comparison, reporting). Pure-logic pieces (permutation construction, validation checks, metric formulas, Jaccard/height-diff) get plain-assert unit tests that run without Gurobi. Solver-driving pieces reuse the existing codebase's idioms exactly: one long-lived `two_stage_model` instance per run, mutate `budget_ref.rhs` per budget (as `stochastic_model.ipynb` / `Bounds.ipynb` already do), and read `.sol` files back via `model.read` + `getVarByName` (as `output_analysis/analysis.py` already does). All outputs land in `vsc_results/` at the repo root, matching the spec's Deliverables section.

**Tech Stack:** Python 3, `gurobipy` (MILP solves — **not currently installed in this environment**, see Task 1), `pandas`/`numpy` (data manipulation), `scipy.stats.spearmanr` (correlation), `matplotlib` (figures — `folium` used by `Visualization.ipynb` for maps is **not installed**; Task 10 uses a plain `matplotlib` scatter instead).

**Spec:** [Revision_work/spatial_correlation_experiment.md](spatial_correlation_experiment.md)

## Global Constraints

- Every `two_stage_model` instantiated for this experiment must hold `fixed_cost`, `variable_cost`, `mit_coarse`, `flexible_generation`, `robust_flag: False`, `set_objective: 'min'`, `reference_bus`, `mip_gap`, `time_limit`, `solver_method` fixed at `config.yaml`'s current values (`fixed_cost=25000`, `variable_cost=100000`, `mit_coarse=1`, `flexible_generation=True`, `reference_bus=313`, `mip_gap=0.005`, `time_limit=21600`, `solver_method=2`). Only `input1`'s flood columns (and, transiently, the budget) may differ between runs.
- Budget sweep is exactly `[0, 10, 20, 30, 40, 50, 60, 70, 80]` (millions of dollars), matching `output/sm_16/` and `output_analysis/wait_and_see_dict.json`.
- Data source is `fixed_reduced_grid/16_Scenario/` (663 buses, 362 substations, 16 flood scenario columns). Do not edit checked-in notebooks (`stochastic_model.ipynb`, `robust_model.ipynb`, `output_analysis/*.ipynb`) — all hardcoded-path fixes happen only in the new scripts under `Revision_work/vsc/`.
- `I_f` (flooded substations) = 72, computed as substations where `groupby("SubNum")[flood_cols].max().max(axis=1) > 0`. **Do not use `analysis.py`'s `n_flooded_substations` attribute** — it filters bus rows, not substations, and returns 182 (flooded buses) for the 16-scenario set, not 72.
- `config.yaml` sets no Gurobi `Threads` parameter, so every solve claims all available cores by default. Replications must run sequentially unless the user explicitly authorizes concurrent solves with an explicit `Threads` value (Computational note 3 in the spec).
- Every substation-level quantity (flood height, hardening decision) must be applied identically to every bus row sharing that `SubNum` — never permute or fix at the bus-row level.
- Save results after every solve (CSV append or per-replication JSON) so an interrupted run resumes without recomputation.

---

## File Structure

```
Revision_work/vsc/
  paths.py                    # repo-relative path resolution (replaces hardcoded author paths)
  env_check.py                # Task 1: verifies gurobipy is importable and licensed
  baseline.py                 # Task 2 (Step 1): L*_SO, L_SO(x_bar), L*_WS, worst-case per budget
  decorrelate.py              # Task 3 (Step 2): permutation construction + validation checks
  solve_decorrelated.py       # Task 4 (Step 3): SO solves on decorrelated scenarios
  evaluate_decorrelated.py    # Task 5 (Step 4): fix-and-resolve on true scenarios
  metrics.py                  # Task 6 (Step 5): VSC/VMV/VSS/EVPI/misestimation/worst-case-gap
  decisions.py                # Task 7 (Step 6): Jaccard, height diff, frequency map, geography
  independent_sampling.py     # Task 11 (Step 7, optional): larger-N robustness check
  run_pilot.py                 # Task 8: 2-replication x {20,40,60} pilot orchestrator
  run_full.py                  # Task 9: 20-replication x 9-budget full orchestrator
  report.py                    # Task 10: figures, LaTeX tables, summary_for_rebuttal.md
  tests/
    test_decorrelate.py        # unit tests for decorrelate.py (no Gurobi)
    test_metrics.py            # unit tests for metrics.py (no Gurobi)
    test_decisions.py          # unit tests for decisions.py (no Gurobi)

vsc_results/                   # created by the scripts; not checked into git logic, only outputs
  pilot/                       # Task 8 output
  raw_results.csv               # Task 9/6 deliverable 1
  summary_table.csv / .tex      # Task 6/10 deliverable 2
  figure5_updated.pdf / .png    # Task 10 deliverable 3
  decomposition.pdf / .png      # Task 10 deliverable 4
  decision_comparison.tex       # Task 10 deliverable 5
  substation_map.png            # Task 10 deliverable 6
  validation_report.md          # Task 3/2/6 deliverable 7
  summary_for_rebuttal.md       # Task 10 deliverable 8
  decorrelated_scenarios/       # cached Delta_tilde_r matrices (Task 3)
  decorrelated_solutions/       # .sol files + x_IND per (r, budget) (Task 4)
```

---

### Task 1: Environment prerequisite check

**Files:**
- Create: `Revision_work/vsc/env_check.py`

**Interfaces:**
- Produces: `check_environment() -> None` (raises `RuntimeError` with an actionable message if `gurobipy` cannot be imported or cannot obtain a license), used as the first line of every downstream driver script (`baseline.py`, `solve_decorrelated.py`, `evaluate_decorrelated.py`, `run_pilot.py`, `run_full.py`).

- [ ] **Step 1: Write the check**

```python
# Revision_work/vsc/env_check.py
def check_environment():
    try:
        import gurobipy as gp
    except ImportError as e:
        raise RuntimeError(
            "gurobipy is not importable in this Python environment. "
            "Neither the system python3 (/usr/bin/python3) nor the active "
            "conda env (/opt/miniconda3) has gurobipy or pyomo installed as of "
            "this plan's authoring. Install gurobipy (`pip install gurobipy` or "
            "`conda install -c gurobi gurobi`) and ensure a valid Gurobi license "
            "is available before running any part of this experiment."
        ) from e
    try:
        m = gp.Model()
        m.dispose()
    except gp.GurobiError as e:
        raise RuntimeError(
            f"gurobipy imported but could not create a model (license problem?): {e}"
        ) from e
```

- [ ] **Step 2: Run it manually to confirm it currently fails**

Run: `python3 Revision_work/vsc/env_check.py` after adding a one-line `if __name__ == "__main__": check_environment(); print("OK")` — or just `python3 -c "from Revision_work.vsc.env_check import check_environment; check_environment()"`
Expected: `RuntimeError` naming the missing `gurobipy` import, since this repo's checked python3 and conda base env both lack it.

- [ ] **Step 3: Report the blocker and stop**

Do not proceed to Task 2 (or any task that instantiates `two_stage_model`) until the user confirms which environment has a working `gurobipy` + license, and that environment's `python` executable is used for the rest of this plan. This directly implements the spec's Instruction 4 ("ask me to confirm before running anything expensive") — nothing in this pipeline runs at all without this.

- [ ] **Step 4: Commit**

```bash
git add Revision_work/vsc/env_check.py
git commit -m "vsc: add gurobipy environment precheck"
```

---

### Task 2: Path resolution helper (spec Instruction 3)

**Files:**
- Create: `Revision_work/vsc/paths.py`

**Interfaces:**
- Produces: `REPO_ROOT: Path`, `INPUT_DIR_16: Path` (`fixed_reduced_grid/16_Scenario/`, trailing slash for `prepare_input`'s string-concat signature), `SM16_OUTPUT_DIR: Path` (`output/sm_16/`), `WAIT_AND_SEE_JSON: Path` (`output_analysis/wait_and_see_dict.json`), `VSC_RESULTS_DIR: Path` (`vsc_results/`, created if missing). Consumed by every other module in this plan instead of hardcoded `/Users/ashutoshshukla/...` paths.

- [ ] **Step 1: Write the module**

```python
# Revision_work/vsc/paths.py
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR_16 = REPO_ROOT / "fixed_reduced_grid" / "16_Scenario"
SM16_OUTPUT_DIR = REPO_ROOT / "output" / "sm_16"
WAIT_AND_SEE_JSON = REPO_ROOT / "output_analysis" / "wait_and_see_dict.json"
VSC_RESULTS_DIR = REPO_ROOT / "vsc_results"

VSC_RESULTS_DIR.mkdir(exist_ok=True)


def input_dir_str(path: Path = INPUT_DIR_16) -> str:
    """utils.prepare_input does `path_str + "Final_Input1.csv"`, so it needs a trailing slash."""
    s = str(path)
    return s if s.endswith("/") else s + "/"
```

- [ ] **Step 2: Verify paths resolve correctly**

Run: `python3 -c "from Revision_work.vsc.paths import INPUT_DIR_16, input_dir_str; import os; print(os.path.exists(input_dir_str(INPUT_DIR_16) + 'Final_Input1.csv'))"`
Expected: `True`

- [ ] **Step 3: Commit**

```bash
git add Revision_work/vsc/paths.py
git commit -m "vsc: add repo-relative path helper for the VSC experiment"
```

---

### Task 3: Decorrelated scenario construction + validation (spec Step 2)

**Files:**
- Create: `Revision_work/vsc/decorrelate.py`
- Test: `Revision_work/vsc/tests/test_decorrelate.py`

**Interfaces:**
- Consumes: a `pandas.DataFrame` shaped like `prepare_input`'s `input1` (must have `SubNum` and the `max_flood_level_*` columns).
- Produces: `flooded_substations(input1: pd.DataFrame, filter_col: list[str]) -> set` (I_f); `build_decorrelated_flood_df(input1: pd.DataFrame, filter_col: list[str], seed: int) -> pd.DataFrame` (same shape as `input1[filter_col]`, decorrelated); `validate_decorrelation(input1: pd.DataFrame, decorrelated: pd.DataFrame, filter_col: list[str]) -> dict` (the 5 checks from spec Step 2, returns a dict of pass/fail + numbers). Consumed by `solve_decorrelated.py` (Task 4) and `report.py`'s validation report (Task 10).

- [ ] **Step 1: Write the failing tests**

```python
# Revision_work/vsc/tests/test_decorrelate.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from decorrelate import flooded_substations, build_decorrelated_flood_df, validate_decorrelation


def _toy_input1():
    # 2 substations, 2 buses each, 4 scenarios. Substation 20 never floods.
    return pd.DataFrame({
        "SubNum":   [10, 10, 20, 20],
        "max_flood_level_a": [5.0, 5.0, 0.0, 0.0],
        "max_flood_level_b": [0.0, 0.0, 0.0, 0.0],
        "max_flood_level_c": [8.0, 8.0, 0.0, 0.0],
        "max_flood_level_d": [3.0, 3.0, 0.0, 0.0],
    })


def test_flooded_substations_excludes_never_flooded():
    input1 = _toy_input1()
    filter_col = ["max_flood_level_a", "max_flood_level_b", "max_flood_level_c", "max_flood_level_d"]
    assert flooded_substations(input1, filter_col) == {10}


def test_decorrelated_preserves_marginals_and_zeros_unflooded():
    input1 = _toy_input1()
    filter_col = ["max_flood_level_a", "max_flood_level_b", "max_flood_level_c", "max_flood_level_d"]
    out = build_decorrelated_flood_df(input1, filter_col, seed=1)
    assert set(out.columns) == set(filter_col)
    # substation 20 stays all zero
    assert (out.loc[input1["SubNum"] == 20] == 0).all().all()
    # substation 10's multiset of values is unchanged (some permutation of {5,0,8,3})
    sub10 = out.loc[input1["SubNum"] == 10].iloc[0]
    assert sorted(sub10.values) == [0.0, 3.0, 5.0, 8.0]


def test_decorrelated_shares_value_across_buses_in_same_substation():
    input1 = _toy_input1()
    filter_col = ["max_flood_level_a", "max_flood_level_b", "max_flood_level_c", "max_flood_level_d"]
    out = build_decorrelated_flood_df(input1, filter_col, seed=7)
    sub10_rows = out.loc[input1["SubNum"] == 10]
    assert (sub10_rows.iloc[0] == sub10_rows.iloc[1]).all()


def test_validate_decorrelation_reports_pass():
    input1 = _toy_input1()
    filter_col = ["max_flood_level_a", "max_flood_level_b", "max_flood_level_c", "max_flood_level_d"]
    out = build_decorrelated_flood_df(input1, filter_col, seed=3)
    report = validate_decorrelation(input1, out, filter_col)
    assert report["marginals_preserved"] is True
    assert report["same_flooded_set"] is True
    assert report["shared_height_invariant"] is True


if __name__ == "__main__":
    test_flooded_substations_excludes_never_flooded()
    test_decorrelated_preserves_marginals_and_zeros_unflooded()
    test_decorrelated_shares_value_across_buses_in_same_substation()
    test_validate_decorrelation_reports_pass()
    print("All decorrelate.py tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 Revision_work/vsc/tests/test_decorrelate.py`
Expected: `ModuleNotFoundError: No module named 'decorrelate'` (the module doesn't exist yet).

- [ ] **Step 3: Write the implementation**

```python
# Revision_work/vsc/decorrelate.py
import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def flooded_substations(input1: pd.DataFrame, filter_col: list) -> set:
    sub_max = input1.groupby("SubNum")[filter_col].max().max(axis=1)
    return set(sub_max[sub_max > 0].index)


def build_decorrelated_flood_df(input1: pd.DataFrame, filter_col: list, seed: int) -> pd.DataFrame:
    """Independently permutes each flooded substation's scenario-to-height mapping.

    Substations outside I_f are left at zero. Every bus row belonging to the
    same SubNum receives the identical permuted value, matching the shared
    per-substation flood height the model constraints assume.
    """
    rng = np.random.default_rng(seed)
    i_f = flooded_substations(input1, filter_col)

    sub_values = input1.groupby("SubNum")[filter_col].first()  # one row per substation
    permuted = sub_values.copy()
    n_scen = len(filter_col)
    for sub in sub_values.index:
        if sub in i_f:
            perm = rng.permutation(n_scen)
            permuted.loc[sub, filter_col] = sub_values.loc[sub, filter_col].values[perm]
        else:
            permuted.loc[sub, filter_col] = 0.0

    out = input1[["SubNum"]].merge(permuted, left_on="SubNum", right_index=True, how="left")
    out.index = input1.index
    return out[filter_col]


def _mean_pairwise_spearman(flood_by_sub: pd.DataFrame) -> float:
    """flood_by_sub: rows = substations in I_f, columns = scenarios."""
    subs = flood_by_sub.index.tolist()
    corrs = []
    for a in range(len(subs)):
        for b in range(a + 1, len(subs)):
            va, vb = flood_by_sub.loc[subs[a]], flood_by_sub.loc[subs[b]]
            if va.nunique() <= 1 or vb.nunique() <= 1:
                continue
            rho, _ = spearmanr(va, vb)
            if not np.isnan(rho):
                corrs.append(rho)
    return float(np.mean(corrs)) if corrs else float("nan")


def validate_decorrelation(input1: pd.DataFrame, decorrelated: pd.DataFrame, filter_col: list) -> dict:
    i_f = flooded_substations(input1, filter_col)

    orig_by_sub = input1.groupby("SubNum")[filter_col].first()
    dec_by_sub = input1[["SubNum"]].join(decorrelated).groupby("SubNum")[filter_col].first()

    # 1. Marginals preserved (sorted per-substation vector unchanged)
    marginals_preserved = all(
        sorted(orig_by_sub.loc[s].values) == sorted(dec_by_sub.loc[s].values)
        for s in orig_by_sub.index
    )

    # 2. Same flooded set
    dec_input1 = input1[["SubNum"]].join(decorrelated)
    same_flooded_set = flooded_substations(dec_input1, filter_col) == i_f

    # 3. Correlation destroyed
    orig_corr = _mean_pairwise_spearman(orig_by_sub.loc[list(i_f)])
    dec_corr = _mean_pairwise_spearman(dec_by_sub.loc[list(i_f)])

    # 4. Simultaneous failures
    orig_counts = (orig_by_sub.loc[list(i_f)] > 0).sum(axis=0)
    dec_counts = (dec_by_sub.loc[list(i_f)] > 0).sum(axis=0)

    # 5. Shared-height invariant (every bus row in a substation matches every other)
    check_df = input1[["SubNum"]].join(decorrelated)
    shared_height_invariant = bool(
        check_df.groupby("SubNum")[filter_col].nunique().le(1).all().all()
    )

    return {
        "marginals_preserved": bool(marginals_preserved),
        "same_flooded_set": bool(same_flooded_set),
        "shared_height_invariant": shared_height_invariant,
        "orig_mean_spearman": orig_corr,
        "decorrelated_mean_spearman": dec_corr,
        "orig_simultaneous_failures_mean": float(orig_counts.mean()),
        "orig_simultaneous_failures_std": float(orig_counts.std()),
        "orig_simultaneous_failures_max": float(orig_counts.max()),
        "decorrelated_simultaneous_failures_mean": float(dec_counts.mean()),
        "decorrelated_simultaneous_failures_std": float(dec_counts.std()),
        "decorrelated_simultaneous_failures_max": float(dec_counts.max()),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 Revision_work/vsc/tests/test_decorrelate.py`
Expected: `All decorrelate.py tests passed.`

- [ ] **Step 5: Sanity-check against the real 16-scenario data (no Gurobi needed)**

```python
# scratch check, not committed
import pandas as pd, sys
sys.path.insert(0, "Revision_work/vsc")
from decorrelate import flooded_substations, build_decorrelated_flood_df, validate_decorrelation

input1 = pd.read_csv("fixed_reduced_grid/16_Scenario/Final_Input1.csv")
filter_col = [c for c in input1.columns if c.startswith("max")]
i_f = flooded_substations(input1, filter_col)
print(len(i_f))  # expect 72
dec = build_decorrelated_flood_df(input1, filter_col, seed=1)
report = validate_decorrelation(input1, dec, filter_col)
print(report)
```

Run this and confirm `len(i_f) == 72`, `marginals_preserved`/`same_flooded_set`/`shared_height_invariant` are all `True`, `orig_mean_spearman` is clearly positive, and `decorrelated_mean_spearman` is close to zero.

- [ ] **Step 6: Commit**

```bash
git add Revision_work/vsc/decorrelate.py Revision_work/vsc/tests/test_decorrelate.py
git commit -m "vsc: add decorrelated flood-scenario construction and validation"
```

---

### Task 4: Baseline reproduction (spec Step 1) — requires Gurobi

**Files:**
- Create: `Revision_work/vsc/baseline.py`

**Interfaces:**
- Consumes: `paths.py` (Task 2), `decorrelate.flooded_substations` (Task 3, for reporting `I_f` size), the existing `utils.prepare_input`, `main_model.two_stage_model`, `output/sm_16/*.sol`, `output_analysis/wait_and_see_dict.json`.
- Produces: `load_config() -> dict` (model_params built from `config.yaml` + `paths.py`, not from `output/sm_16/model_params.json` — see note below); `reproduce_baseline(model_params: dict, budget_vector: list) -> pd.DataFrame` with columns `budget, L_SO_star, L_SO_xbar, L_WS_star, worst_case_L_SO` plus one `x_SO__<SubNum>` column per substation. Consumed by `metrics.py` (Task 6) and `run_pilot.py`/`run_full.py` (Tasks 8/9).

**Note on `model_params.json`:** `output/sm_16/model_params.json` does not contain `mit_coarse` (it was apparently dropped before an earlier dump); `analysis.py` patches this by re-setting `model_params["mit_coarse"] = 1` after loading. Rather than depend on that patched JSON, `load_config()` reads `config.yaml` directly (which has `mit_coarse: 1` today) — per the Global Constraints, that is the single source of truth this experiment must match.

- [ ] **Step 1: Write the module**

```python
# Revision_work/vsc/baseline.py
import sys
import yaml
import numpy as np
import pandas as pd

from paths import REPO_ROOT, SM16_OUTPUT_DIR, WAIT_AND_SEE_JSON, input_dir_str, INPUT_DIR_16
from env_check import check_environment

sys.path.insert(0, str(REPO_ROOT))


def load_config() -> dict:
    check_environment()
    from utils import prepare_input

    with open(REPO_ROOT / "config.yaml") as f:
        model_params = yaml.safe_load(f)
    model_params["path_to_input"] = input_dir_str(INPUT_DIR_16)
    model_params["input1"], model_params["input2"] = prepare_input(model_params["path_to_input"])
    return model_params


def _worst_case_load_shed(base_model) -> float:
    """max over scenarios k of sum_j (D_j - s[j,k]), read from an already-solved model."""
    import gurobipy as gp
    input1_load = base_model.input1["load"].values
    per_scenario = []
    for k in range(base_model.n_scenarios):
        shed = sum(
            input1_load[i] - base_model.s[i, k].X
            for i in range(base_model.n_buses)
        )
        per_scenario.append(shed)
    return max(per_scenario)


def reproduce_baseline(model_params: dict, budget_vector: list) -> pd.DataFrame:
    from main_model import two_stage_model

    base_model = two_stage_model(model_params)
    base_model.model.setParam("LogToConsole", 0)

    # --- L*_SO(I) and x_SO via .sol reload (analysis.py's pattern) ---
    rows = []
    sub_ids = list(base_model.unique_substations)
    for budget in budget_vector:
        sol_path = SM16_OUTPUT_DIR / f"{budget}M_solution.sol"
        base_model.model.read(str(sol_path))
        base_model.model.update()
        row = {"budget": budget, "L_SO_star": base_model.model.getVarByName("dummy_never_used")}
        # objective value after read+update isn't populated until optimize(); re-derive from x/s below instead.
        for sub_id in sub_ids:
            row[f"x_SO__{sub_id}"] = base_model.model.getVarByName(f"x[{sub_id}]").Start
        row["worst_case_L_SO"] = _worst_case_load_shed_from_start(base_model)
        rows.append(row)

    df = pd.DataFrame(rows).set_index("budget")

    # L*_SO(I): reuse the manuscript-reported values already aggregated in
    # output/sm_16/stochastic_solution.csv (produced by the same .sol files).
    ss = pd.read_csv(SM16_OUTPUT_DIR / "stochastic_solution.csv", header=None, index_col=0).iloc[:, 0]
    df["L_SO_star"] = [ss.loc[b] for b in df.index]

    # --- L*_WS(I) from the cached wait-and-see dict ---
    import json
    with open(WAIT_AND_SEE_JSON) as f:
        was_dict = json.load(f)
    df["L_WS_star"] = [np.mean(list(was_dict[str(b)].values())) for b in df.index]

    # --- L_SO(x_bar): mean-value solution, evaluated on the original scenarios ---
    df["L_SO_xbar"] = _mean_value_bound(model_params, budget_vector)

    return df.reset_index()


def _worst_case_load_shed_from_start(base_model) -> float:
    input1_load = base_model.input1["load"].values
    per_scenario = []
    for k in range(base_model.n_scenarios):
        shed = sum(
            input1_load[i] - base_model.s[i, k].Start
            for i in range(base_model.n_buses)
        )
        per_scenario.append(shed)
    return max(per_scenario)


def _mean_value_bound(model_params: dict, budget_vector: list) -> dict:
    """Reproduces Bounds.ipynb's mean-value pipeline: solve EV on the rounded
    mean scenario, then fix x to that solution and re-optimize on the full
    16-scenario model."""
    from main_model import two_stage_model

    flood_df = model_params["input1"][model_params["input1"].columns[model_params["input1"].columns.str.startswith("max")]]
    input1_no_flood = model_params["input1"].drop(columns=flood_df.columns)

    ev_params = dict(model_params)
    ev_input1 = input1_no_flood.copy()
    ev_input1["max_mean_value_solution"] = np.ceil(flood_df.mean(axis=1))
    ev_params["input1"] = ev_input1

    mean_solution = {}
    for budget in budget_vector:
        from main_model import two_stage_model as tsm
        ev_model = tsm(ev_params)
        ev_model.model.setParam("LogToConsole", 0)
        ev_model.budget_ref.rhs = budget * 1e6
        ev_model.model.setParam("MIPGap", model_params["mip_gap"])
        ev_model.model.setParam("TimeLimit", model_params["time_limit"])
        ev_model.model.setParam("Method", model_params["solver_method"])
        ev_model.model.optimize()
        mean_solution[budget] = {sub: ev_model.x[sub].X for sub in ev_model.x}

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
```

*(The stray `row = {"budget": budget, "L_SO_star": base_model.model.getVarByName("dummy_never_used")}` line above is wrong and must not survive review — fix it in Step 3's review pass: drop that key entirely since `L_SO_star` is populated afterward from `stochastic_solution.csv`.)*

- [ ] **Step 2: Fix the draft bug found while writing Step 1**

Remove the placeholder `"L_SO_star": base_model.model.getVarByName("dummy_never_used")` key from the `row` dict in `reproduce_baseline` — it was a scaffolding mistake; `L_SO_star` is assigned two lines later from `stochastic_solution.csv` and the dict should only be seeded with `{"budget": budget}`.

- [ ] **Step 3: Confirm `output/sm_16/stochastic_solution.csv` layout before relying on it**

Run: `python3 -c "import pandas as pd; print(pd.read_csv('output/sm_16/stochastic_solution.csv', header=None))"`
Expected: two columns, budget and objective value, one row per budget in `{0,...,80}` — matching how `Bounds.ipynb` consumes it (`df.iloc[i,0]` → budget, `df.iloc[i,1]` → value). If the header/shape differs, adjust the `pd.read_csv(..., header=None, index_col=0)` call in `reproduce_baseline` accordingly before proceeding.

- [ ] **Step 4: Run against the real 16-scenario baseline (requires a working Gurobi env from Task 1)**

Run: `python3 -c "
from Revision_work.vsc.baseline import load_config, reproduce_baseline
mp = load_config()
df = reproduce_baseline(mp, [0,10,20,30,40,50,60,70,80])
print(df)
"`
Expected: at budget 0, `L_SO_star`, `L_SO_xbar`, and `L_WS_star` are numerically equal (per spec Step 1's sanity check); values are close to Figure 5 of the manuscript. If they don't match, stop and report the discrepancy per the spec — do not proceed to Task 5+ until this is resolved.

- [ ] **Step 5: Commit**

```bash
git add Revision_work/vsc/baseline.py
git commit -m "vsc: reproduce SO/EV/WS baseline curves from cached solutions"
```

---

### Task 5: Solve SO on decorrelated scenarios (spec Step 3) — requires Gurobi

**Files:**
- Create: `Revision_work/vsc/solve_decorrelated.py`

**Interfaces:**
- Consumes: `paths.py` (Task 2), `decorrelate.build_decorrelated_flood_df` (Task 3), `baseline.load_config` (Task 4).
- Produces: `solve_one_replication(model_params: dict, seed: int, budget_vector: list, out_dir: Path) -> pd.DataFrame` with columns `replication, budget, solve_time_s, mip_gap, status` plus one `x_IND__<SubNum>` column per substation and `L_IND_in`. Writes one `.sol` file per `(replication, budget)` to `out_dir` and appends each row to `out_dir / "solve_decorrelated_results.csv"` immediately after solving (resumability, per Global Constraints). Consumed by `evaluate_decorrelated.py` (Task 6) and `run_pilot.py`/`run_full.py` (Tasks 8/9).

- [ ] **Step 1: Write the module**

```python
# Revision_work/vsc/solve_decorrelated.py
import csv
import time
from pathlib import Path

import pandas as pd

from paths import REPO_ROOT, VSC_RESULTS_DIR
from env_check import check_environment
from decorrelate import build_decorrelated_flood_df

import sys
sys.path.insert(0, str(REPO_ROOT))


RESULT_COLUMNS_CACHE = None  # filled in on first call, used to keep the CSV header stable


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
```

- [ ] **Step 2: Dry-run on a single cheap budget (requires Gurobi env)**

Run: `python3 -c "
from Revision_work.vsc.baseline import load_config
from Revision_work.vsc.solve_decorrelated import solve_one_replication
from Revision_work.vsc.paths import VSC_RESULTS_DIR
mp = load_config()
df = solve_one_replication(mp, seed=1, budget_vector=[0], out_dir=VSC_RESULTS_DIR / 'smoke_test')
print(df[['replication','budget','solve_time_s','mip_gap','status','L_IND_in']])
"`
Expected: one row, `status == 2` (`GRB.OPTIMAL`) or a status consistent with `time_limit`, `L_IND_in` close to (but not necessarily equal to) `L_SO_star` at budget 0 (both should be near the total load at budget 0 with no hardening — actually equal, since at budget 0 no hardening is possible regardless of scenario ordering, matching the spec's Step 1 sanity check logic).

- [ ] **Step 3: Delete the smoke-test output**

```bash
rm -rf vsc_results/smoke_test
```

- [ ] **Step 4: Commit**

```bash
git add Revision_work/vsc/solve_decorrelated.py
git commit -m "vsc: solve SO on decorrelated scenarios with resumable per-solve logging"
```

---

### Task 6: Evaluate decorrelated decisions on the true scenarios (spec Step 4) — requires Gurobi

**Files:**
- Create: `Revision_work/vsc/evaluate_decorrelated.py`

**Interfaces:**
- Consumes: `baseline.load_config` (Task 4), the `solve_decorrelated_results.csv` produced by Task 5 (for `x_IND__<SubNum>` values per `(replication, budget)`).
- Produces: `evaluate_all(model_params: dict, decorrelated_results: pd.DataFrame) -> pd.DataFrame` — one row per `(replication, budget)` with `L_SO_xind` and `worst_case_L_xind`, built from a *single* reused `two_stage_model` instance (fix-and-resolve, matching `Bounds.ipynb`'s `mean_value_bound` loop). Consumed by `metrics.py` (Task 7).

- [ ] **Step 1: Write the module**

```python
# Revision_work/vsc/evaluate_decorrelated.py
import pandas as pd

from env_check import check_environment


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
```

- [ ] **Step 2: Dry-run against the Task 5 smoke-test result shape**

Run (requires Task 5's smoke-test to have been re-run, or use one real replication's row):
```python
from Revision_work.vsc.baseline import load_config
from Revision_work.vsc.solve_decorrelated import solve_one_replication
from Revision_work.vsc.evaluate_decorrelated import evaluate_all
from Revision_work.vsc.paths import VSC_RESULTS_DIR

mp = load_config()
dec = solve_one_replication(mp, seed=1, budget_vector=[0, 20], out_dir=VSC_RESULTS_DIR / "smoke_test2")
ev = evaluate_all(mp, dec)
print(ev)
```
Expected: two rows; at `budget == 0`, `L_SO_xind` equals `L_SO_star` from `baseline.py` at budget 0 (no hardening possible regardless of `x_IND`, since the budget forces `x = 0` everywhere). Clean up: `rm -rf vsc_results/smoke_test2`.

- [ ] **Step 3: Commit**

```bash
git add Revision_work/vsc/evaluate_decorrelated.py
git commit -m "vsc: evaluate decorrelated decisions on the true MEOW scenarios via fix-and-resolve"
```

---

### Task 7: Metrics computation (spec Step 5) — no Gurobi needed

**Files:**
- Create: `Revision_work/vsc/metrics.py`
- Test: `Revision_work/vsc/tests/test_metrics.py`

**Interfaces:**
- Consumes: the baseline DataFrame from `baseline.reproduce_baseline` (Task 4: `budget, L_SO_star, L_SO_xbar, L_WS_star, worst_case_L_SO`) and the evaluation DataFrame from `evaluate_decorrelated.evaluate_all` (Task 6: `replication, budget, L_SO_xind, worst_case_L_xind`) joined with `solve_decorrelated_results.csv`'s `L_IND_in` (Task 5).
- Produces: `compute_metrics(baseline_df, eval_df, mip_gap: float) -> pd.DataFrame` — one row per `(replication, budget)` with `VSC, VMV, VSS, VSC_share, misestimation, misestimation_pct, worst_case_gap, EVPI`, and a `vsc_negative_flag` column. `summarize(metrics_df) -> pd.DataFrame` — one row per budget with mean/min/max across replications.

- [ ] **Step 1: Write the failing tests**

```python
# Revision_work/vsc/tests/test_metrics.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from metrics import compute_metrics, summarize


def test_compute_metrics_basic_decomposition():
    baseline_df = pd.DataFrame({
        "budget": [20],
        "L_SO_star": [3.0],
        "L_SO_xbar": [5.0],
        "L_WS_star": [1.0],
        "worst_case_L_SO": [4.0],
    })
    eval_df = pd.DataFrame({
        "replication": [1],
        "budget": [20],
        "L_SO_xind": [3.8],
        "worst_case_L_xind": [4.5],
        "L_IND_in": [3.5],
    })
    out = compute_metrics(baseline_df, eval_df, mip_gap=0.005)
    row = out.iloc[0]
    assert row["VSC"] == 3.8 - 3.0
    assert row["VMV"] == 5.0 - 3.8
    assert row["VSS"] == 5.0 - 3.0
    assert abs(row["VMV"] + row["VSC"] - row["VSS"]) < 1e-9
    assert row["misestimation"] == 3.5 - 3.8
    assert row["worst_case_gap"] == 4.5 - 4.0
    assert row["EVPI"] == 3.0 - 1.0


def test_negative_vsc_beyond_gap_is_flagged():
    baseline_df = pd.DataFrame({
        "budget": [20], "L_SO_star": [3.0], "L_SO_xbar": [5.0],
        "L_WS_star": [1.0], "worst_case_L_SO": [4.0],
    })
    eval_df = pd.DataFrame({
        "replication": [1], "budget": [20],
        "L_SO_xind": [2.5],  # below L_SO_star -> VSC negative beyond a 0.005 gap
        "worst_case_L_xind": [4.0], "L_IND_in": [2.5],
    })
    out = compute_metrics(baseline_df, eval_df, mip_gap=0.005)
    assert out.iloc[0]["vsc_negative_flag"] is True


def test_summarize_aggregates_across_replications():
    baseline_df = pd.DataFrame({
        "budget": [20, 20], "L_SO_star": [3.0, 3.0], "L_SO_xbar": [5.0, 5.0],
        "L_WS_star": [1.0, 1.0], "worst_case_L_SO": [4.0, 4.0],
    })
    eval_df = pd.DataFrame({
        "replication": [1, 2], "budget": [20, 20],
        "L_SO_xind": [3.5, 4.0], "worst_case_L_xind": [4.2, 4.4],
        "L_IND_in": [3.4, 3.9],
    })
    metrics_df = compute_metrics(baseline_df, eval_df, mip_gap=0.005)
    summary = summarize(metrics_df)
    row = summary.iloc[0]
    assert row["VSC_mean"] == ((3.5 - 3.0) + (4.0 - 3.0)) / 2
    assert row["VSC_min"] == 3.5 - 3.0
    assert row["VSC_max"] == 4.0 - 3.0


if __name__ == "__main__":
    test_compute_metrics_basic_decomposition()
    test_negative_vsc_beyond_gap_is_flagged()
    test_summarize_aggregates_across_replications()
    print("All metrics.py tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 Revision_work/vsc/tests/test_metrics.py`
Expected: `ModuleNotFoundError: No module named 'metrics'`

- [ ] **Step 3: Write the implementation**

```python
# Revision_work/vsc/metrics.py
import pandas as pd


def compute_metrics(baseline_df: pd.DataFrame, eval_df: pd.DataFrame, mip_gap: float) -> pd.DataFrame:
    merged = eval_df.merge(baseline_df, on="budget", how="left")

    merged["VSC"] = merged["L_SO_xind"] - merged["L_SO_star"]
    merged["VMV"] = merged["L_SO_xbar"] - merged["L_SO_xind"]
    merged["VSS"] = merged["L_SO_xbar"] - merged["L_SO_star"]
    merged["VSC_share"] = merged["VSC"] / merged["VSS"].where(merged["VSS"] > 0)
    merged["misestimation"] = merged["L_IND_in"] - merged["L_SO_xind"]
    merged["misestimation_pct"] = 100 * merged["misestimation"] / merged["L_SO_xind"]
    merged["worst_case_gap"] = merged["worst_case_L_xind"] - merged["worst_case_L_SO"]
    merged["EVPI"] = merged["L_SO_star"] - merged["L_WS_star"]

    tolerance = mip_gap * merged["L_SO_star"].abs().clip(lower=1e-9)
    merged["vsc_negative_flag"] = merged["VSC"] < -tolerance

    return merged


def summarize(metrics_df: pd.DataFrame) -> pd.DataFrame:
    grouped = metrics_df.groupby("budget")
    summary = grouped.agg(
        L_SO_star=("L_SO_star", "first"),
        L_SO_xbar=("L_SO_xbar", "first"),
        L_WS_star=("L_WS_star", "first"),
        VSS=("VSS", "first"),
        L_SO_xind_mean=("L_SO_xind", "mean"),
        L_SO_xind_min=("L_SO_xind", "min"),
        L_SO_xind_max=("L_SO_xind", "max"),
        VSC_mean=("VSC", "mean"),
        VSC_min=("VSC", "min"),
        VSC_max=("VSC", "max"),
        VMV_mean=("VMV", "mean"),
        VSC_share_mean=("VSC_share", "mean"),
        n_negative_vsc_flags=("vsc_negative_flag", "sum"),
    ).reset_index()
    return summary
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 Revision_work/vsc/tests/test_metrics.py`
Expected: `All metrics.py tests passed.`

- [ ] **Step 5: Commit**

```bash
git add Revision_work/vsc/metrics.py Revision_work/vsc/tests/test_metrics.py
git commit -m "vsc: compute VSC/VMV/VSS decomposition and summary statistics"
```

---

### Task 8: Decision comparison (spec Step 6) — no Gurobi needed

**Files:**
- Create: `Revision_work/vsc/decisions.py`
- Test: `Revision_work/vsc/tests/test_decisions.py`

**Interfaces:**
- Consumes: `x_SO__<SubNum>` columns from `baseline.reproduce_baseline` (Task 4) and `x_IND__<SubNum>` columns from `solve_decorrelated.solve_one_replication`'s per-replication CSV (Task 5), for a given budget.
- Produces: `jaccard_index(x_so: dict, x_ind: dict) -> float`; `mean_abs_height_diff(x_so: dict, x_ind: dict) -> float`; `budget_allocation(x: dict) -> dict` (`n_hardened`, `mean_height`); `selection_frequency(x_ind_by_rep: dict[int, dict]) -> pd.Series` (fraction of replications selecting each substation); consumed by `report.py` (Task 10) for the decision-comparison table and frequency map.

- [ ] **Step 1: Write the failing tests**

```python
# Revision_work/vsc/tests/test_decisions.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from decisions import jaccard_index, mean_abs_height_diff, budget_allocation, selection_frequency


def test_jaccard_index_partial_overlap():
    x_so = {1: 3, 2: 0, 3: 5}   # selected: {1, 3}
    x_ind = {1: 2, 2: 4, 3: 0}  # selected: {1, 2}
    # intersection {1}, union {1,2,3} -> 1/3
    assert abs(jaccard_index(x_so, x_ind) - 1 / 3) < 1e-9


def test_jaccard_index_identical_sets():
    x_so = {1: 3, 2: 0}
    x_ind = {1: 5, 2: 0}
    assert jaccard_index(x_so, x_ind) == 1.0


def test_mean_abs_height_diff_only_over_common_selection():
    x_so = {1: 3, 2: 0, 3: 5}
    x_ind = {1: 5, 2: 4, 3: 0}
    # only substation 1 selected by both: |3-5| = 2
    assert mean_abs_height_diff(x_so, x_ind) == 2.0


def test_budget_allocation():
    x = {1: 3, 2: 0, 3: 5, 4: 0}
    out = budget_allocation(x)
    assert out["n_hardened"] == 2
    assert out["mean_height"] == 4.0


def test_selection_frequency_across_replications():
    x_ind_by_rep = {
        1: {10: 2, 20: 0},
        2: {10: 0, 20: 3},
        3: {10: 1, 20: 0},
    }
    freq = selection_frequency(x_ind_by_rep)
    assert freq[10] == 2 / 3
    assert freq[20] == 1 / 3


if __name__ == "__main__":
    test_jaccard_index_partial_overlap()
    test_jaccard_index_identical_sets()
    test_mean_abs_height_diff_only_over_common_selection()
    test_budget_allocation()
    test_selection_frequency_across_replications()
    print("All decisions.py tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 Revision_work/vsc/tests/test_decisions.py`
Expected: `ModuleNotFoundError: No module named 'decisions'`

- [ ] **Step 3: Write the implementation**

```python
# Revision_work/vsc/decisions.py
import pandas as pd


def _selected(x: dict) -> set:
    return {sub for sub, height in x.items() if round(height) > 0}


def jaccard_index(x_so: dict, x_ind: dict) -> float:
    a, b = _selected(x_so), _selected(x_ind)
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def mean_abs_height_diff(x_so: dict, x_ind: dict) -> float:
    common = _selected(x_so) & _selected(x_ind)
    if not common:
        return float("nan")
    diffs = [abs(x_so[s] - x_ind[s]) for s in common]
    return sum(diffs) / len(diffs)


def budget_allocation(x: dict) -> dict:
    selected = _selected(x)
    heights = [x[s] for s in selected]
    return {
        "n_hardened": len(selected),
        "mean_height": (sum(heights) / len(heights)) if heights else 0.0,
    }


def selection_frequency(x_ind_by_rep: dict) -> pd.Series:
    all_subs = sorted({sub for x in x_ind_by_rep.values() for sub in x})
    n_reps = len(x_ind_by_rep)
    counts = {sub: 0 for sub in all_subs}
    for x in x_ind_by_rep.values():
        for sub in _selected(x):
            counts[sub] += 1
    return pd.Series({sub: c / n_reps for sub, c in counts.items()})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 Revision_work/vsc/tests/test_decisions.py`
Expected: `All decisions.py tests passed.`

- [ ] **Step 5: Commit**

```bash
git add Revision_work/vsc/decisions.py Revision_work/vsc/tests/test_decisions.py
git commit -m "vsc: add hardening-decision comparison utilities (Jaccard, height diff, frequency map)"
```

---

### Task 9: Pilot run orchestrator (Computational note 5) — requires Gurobi, requires user confirmation

**Files:**
- Create: `Revision_work/vsc/run_pilot.py`

**Interfaces:**
- Consumes: `baseline.load_config`/`reproduce_baseline` (Task 4), `solve_decorrelated.solve_one_replication` (Task 5), `evaluate_decorrelated.evaluate_all` (Task 6), `metrics.compute_metrics`/`summarize` (Task 7).
- Produces: `vsc_results/pilot/` containing `pilot_results.csv` and a printed timing summary. This is a go/no-go checkpoint, not a deliverable.

- [ ] **Step 1: STOP and confirm with the user before running**

Before writing or running this script, confirm explicitly with the user:
1. Which Python environment has a working `gurobipy` + license (Task 1's blocker).
2. That running 2 replications × 3 budgets × (1 SO solve + 1 fix-and-resolve) = 6 solve pairs on this machine now is acceptable (solve time unknown until the pilot itself completes — the manuscript's original 9-budget × 16-scenario SO sweep used `time_limit: 21600` seconds per solve as an upper bound, so a single pilot solve could in the worst case take up to 6 hours; ask whether to lower `time_limit` for the pilot specifically).
This directly implements spec Instruction 4 and Computational note 5.

- [ ] **Step 2: Write the orchestrator**

```python
# Revision_work/vsc/run_pilot.py
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
```

- [ ] **Step 3: Run the pilot**

Run: `python3 Revision_work/vsc/run_pilot.py`
Expected: prints per-replication solve/eval timings and a summary table; `vsc_results/pilot/pilot_results.csv` exists with 6 rows (2 replications × 3 budgets); no `vsc_negative_flag` beyond the MIP gap.

- [ ] **Step 4: Decide fix-and-resolve strategy for Step 4 of the spec**

Compare the printed `eval/solve ratio` across the pilot's 6 (replication, budget) pairs. If fix-and-resolve (Task 6) is *not* materially faster than a fresh SO solve (say, ratio > 0.7), report this to the user and fall back to per-scenario single-scenario solves for Task 10's full run, per spec Step 4 Instruction 3. Otherwise proceed with fix-and-resolve as implemented.

- [ ] **Step 5: Report pilot results to the user and get confirmation before the full run**

Summarize: total pilot wall-clock time, extrapolated full-run estimate (20 replications × 9 budgets vs. the pilot's 2 × 3), and whether VSC in the pilot is in a sane range (nonnegative, not implausibly large relative to `VSS`). Do not proceed to Task 10 without explicit user go-ahead, since the full run is ~15x the pilot's cost.

- [ ] **Step 6: Commit**

```bash
git add Revision_work/vsc/run_pilot.py
git commit -m "vsc: add pilot orchestrator (2 replications x 3 budgets) as a go/no-go checkpoint"
```

---

### Task 10: Full run orchestrator (spec Steps 3-5 at scale) — requires Gurobi, requires user confirmation from Task 9

**Files:**
- Create: `Revision_work/vsc/run_full.py`

**Interfaces:**
- Consumes: same as Task 9, plus resumability (skip `(replication, budget)` pairs already present in `vsc_results/solve_decorrelated_results.csv` / the evaluation CSV).
- Produces: `vsc_results/raw_results.csv` (deliverable 1: one row per `(replication, budget)` with every quantity from spec Steps 3-5, solve time, gap, status) and `vsc_results/summary_table.csv` (deliverable 2, pre-LaTeX).

- [ ] **Step 1: STOP and confirm with the user before running**

Only proceed after Task 9's pilot has been reviewed and the user has explicitly approved the full run (20 replications × 9 budgets = 180 SO solves + up to 180 fix-and-resolve evaluations). Confirm the sequential-only constraint (no `Threads` override) from Global Constraints unless the user authorizes concurrency with an explicit `Threads` value.

- [ ] **Step 2: Write the orchestrator with resumability**

```python
# Revision_work/vsc/run_full.py
import pandas as pd

from paths import VSC_RESULTS_DIR
from baseline import load_config, reproduce_baseline
from solve_decorrelated import solve_one_replication
from evaluate_decorrelated import evaluate_all
from metrics import compute_metrics, summarize

FULL_BUDGETS = [0, 10, 20, 30, 40, 50, 60, 70, 80]
FULL_SEEDS = list(range(1, 21))  # R = 20


def run_full():
    out_dir = VSC_RESULTS_DIR
    solve_dir = out_dir / "decorrelated_solutions"
    solve_csv = solve_dir / "solve_decorrelated_results.csv"

    model_params = load_config()
    baseline_df = reproduce_baseline(model_params, FULL_BUDGETS)
    baseline_df.to_csv(out_dir / "baseline.csv", index=False)

    already_done = set()
    if solve_csv.exists():
        prior = pd.read_csv(solve_csv)
        already_done = set(zip(prior["replication"], prior["budget"]))

    for seed in FULL_SEEDS:
        remaining_budgets = [b for b in FULL_BUDGETS if (seed, b) not in already_done]
        if not remaining_budgets:
            continue
        solve_one_replication(model_params, seed, remaining_budgets, solve_dir)

    solve_df = pd.read_csv(solve_csv)
    eval_df = evaluate_all(model_params, solve_df).merge(
        solve_df[["replication", "budget", "L_IND_in"]], on=["replication", "budget"]
    )
    metrics_df = compute_metrics(baseline_df, eval_df, model_params["mip_gap"])
    metrics_df = metrics_df.merge(
        solve_df[["replication", "budget", "solve_time_s", "mip_gap", "status"]],
        on=["replication", "budget"],
    )
    metrics_df.to_csv(out_dir / "raw_results.csv", index=False)

    summary_df = summarize(metrics_df)
    summary_df.to_csv(out_dir / "summary_table.csv", index=False)

    n_flags = metrics_df["vsc_negative_flag"].sum()
    if n_flags:
        print(f"WARNING: {n_flags} (replication, budget) pairs have VSC negative beyond the MIP gap.")


if __name__ == "__main__":
    run_full()
```

- [ ] **Step 3: Run the full sweep**

Run: `python3 Revision_work/vsc/run_full.py`
Expected: completes (potentially over multiple sessions, since it resumes from `solve_decorrelated_results.csv`); `vsc_results/raw_results.csv` has 180 rows; `vsc_results/summary_table.csv` has 9 rows (one per budget).

- [ ] **Step 4: Commit**

```bash
git add Revision_work/vsc/run_full.py
git commit -m "vsc: add resumable full-sweep orchestrator (20 reps x 9 budgets)"
```

---

### Task 11: Deliverables — figures, tables, validation report, rebuttal summary

**Files:**
- Create: `Revision_work/vsc/report.py`

**Interfaces:**
- Consumes: `vsc_results/raw_results.csv`, `vsc_results/summary_table.csv` (Task 10), `decorrelate.validate_decorrelation` output cached per replication (Task 3 — extend Task 5's `solve_one_replication` call site in `run_full.py` to also dump one `validation_<seed>.json` per replication into `vsc_results/decorrelated_scenarios/`, produced alongside the `.sol` files), `decisions.py` (Task 8), `Final_Input1.csv`'s `Latitude`/`Longitude`.
- Produces: deliverables 3–8 listed in the spec (Figure 5 update, decomposition figure, decision comparison LaTeX table, substation map, validation report, `summary_for_rebuttal.md`).

- [ ] **Step 1: Add validation-report caching to Task 5's driver call**

Before writing `report.py`, extend `run_full.py` (Task 10) to write one validation JSON per replication:

```python
# addition to run_full.py, inside the `for seed in FULL_SEEDS:` loop, before solve_one_replication:
from decorrelate import build_decorrelated_flood_df, validate_decorrelation
filter_col = [c for c in model_params["input1"].columns if c.startswith("max")]
dec = build_decorrelated_flood_df(model_params["input1"], filter_col, seed=seed)
report = validate_decorrelation(model_params["input1"], dec, filter_col)
import json
(solve_dir / f"validation_rep{seed}.json").write_text(json.dumps(report, indent=2))
```

- [ ] **Step 2: Write `report.py`'s figure/table functions**

```python
# Revision_work/vsc/report.py
import json
import pandas as pd
import matplotlib.pyplot as plt

from paths import VSC_RESULTS_DIR, REPO_ROOT
from decisions import jaccard_index, mean_abs_height_diff, budget_allocation, selection_frequency


def figure5_updated(baseline_df: pd.DataFrame, summary_df: pd.DataFrame, out_path):
    budgets = summary_df["budget"]
    plt.figure(figsize=(4, 4))
    plt.plot(budgets, baseline_df.set_index("budget").loc[budgets, "L_SO_xbar"] / 10,
              marker="o", label="Mean value solution", color="#009e73")
    plt.plot(budgets, baseline_df.set_index("budget").loc[budgets, "L_SO_star"] / 10,
              marker="o", label="Stochastic solution", color="#0072b2")
    plt.plot(budgets, baseline_df.set_index("budget").loc[budgets, "L_WS_star"] / 10,
              marker="o", label="Wait-and-see solution", color="#d55e00")
    plt.plot(budgets, summary_df["L_SO_xind_mean"] / 10, marker="s",
              label="Decorrelated solution (mean)", color="#cc79a7")
    plt.fill_between(budgets, summary_df["L_SO_xind_min"] / 10, summary_df["L_SO_xind_max"] / 10,
                       color="#cc79a7", alpha=0.2)
    plt.xlabel("Budget in Millions ($)", fontdict={"fontsize": 11})
    plt.ylabel("Load-shed (GW)", fontdict={"fontsize": 11})
    plt.legend(loc=1, prop={"size": 9}, frameon=False)
    plt.xticks(fontsize=11)
    plt.yticks(fontsize=11)
    plt.tight_layout()
    plt.savefig(str(out_path) + ".pdf")
    plt.savefig(str(out_path) + ".png", dpi=200)
    plt.close()


def decomposition_figure(summary_df: pd.DataFrame, out_path):
    plt.figure(figsize=(5, 4))
    plt.bar(summary_df["budget"], summary_df["VMV_mean"] / 10, label="VMV", color="#009e73")
    plt.bar(summary_df["budget"], summary_df["VSC_mean"] / 10,
            bottom=summary_df["VMV_mean"] / 10, label="VSC", color="#0072b2")
    plt.xlabel("Budget in Millions ($)")
    plt.ylabel("Value of Stochastic Solution (GW)")
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(str(out_path) + ".pdf")
    plt.savefig(str(out_path) + ".png", dpi=200)
    plt.close()


def decision_comparison_table(baseline_df: pd.DataFrame, solve_dir, budgets, out_path):
    rows = []
    for budget in budgets:
        x_so = {
            int(col.split("__")[1]): baseline_df.set_index("budget").loc[budget, col]
            for col in baseline_df.columns if col.startswith("x_SO__")
        }
        solve_csv = pd.read_csv(solve_dir / "solve_decorrelated_results.csv")
        rep_rows = solve_csv[solve_csv["budget"] == budget]
        jaccards, height_diffs = [], []
        x_ind_by_rep = {}
        for _, r in rep_rows.iterrows():
            x_ind = {int(c.split("__")[1]): r[c] for c in rep_rows.columns if c.startswith("x_IND__")}
            x_ind_by_rep[int(r["replication"])] = x_ind
            jaccards.append(jaccard_index(x_so, x_ind))
            height_diffs.append(mean_abs_height_diff(x_so, x_ind))
        so_alloc = budget_allocation(x_so)
        rows.append({
            "budget": budget,
            "jaccard_mean": sum(jaccards) / len(jaccards),
            "n_hardened_SO": so_alloc["n_hardened"],
            "mean_height_SO": so_alloc["mean_height"],
            "mean_abs_height_diff": sum(d for d in height_diffs if d == d) / max(1, sum(1 for d in height_diffs if d == d)),
        })
    df = pd.DataFrame(rows)
    with open(out_path, "w") as f:
        f.write(df.to_latex(index=False, float_format="%.3f"))
    return df


def substation_map(input1: pd.DataFrame, x_so: dict, freq: pd.Series, out_path):
    fig, ax = plt.subplots(figsize=(6, 6))
    sub_coords = input1.groupby("SubNum")[["Latitude", "Longitude"]].first()
    hardened = [s for s in x_so if round(x_so[s]) > 0]
    not_hardened = [s for s in sub_coords.index if s not in hardened]

    ax.scatter(sub_coords.loc[not_hardened, "Longitude"], sub_coords.loc[not_hardened, "Latitude"],
               c="lightgray", s=10, label="Not selected by SO")
    sizes = [20 + 80 * freq.get(s, 0.0) for s in hardened]
    sc = ax.scatter(sub_coords.loc[hardened, "Longitude"], sub_coords.loc[hardened, "Latitude"],
                     c=[freq.get(s, 0.0) for s in hardened], cmap="viridis", s=sizes,
                     label="Selected by SO (color = IND selection frequency)")
    plt.colorbar(sc, ax=ax, label="Fraction of replications IND selects")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(loc="best", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def validation_report(solve_dir, baseline_df, out_path):
    lines = ["# VSC Experiment Validation Report", ""]
    lines.append("## Step 1: Baseline reproduction")
    lines.append(baseline_df.to_markdown(index=False))
    lines.append("")
    lines.append("## Step 2: Decorrelation validation (per replication)")
    for f in sorted(solve_dir.glob("validation_rep*.json")):
        rep = f.stem.replace("validation_rep", "")
        report = json.loads(f.read_text())
        lines.append(f"### Replication {rep}")
        for k, v in report.items():
            lines.append(f"- {k}: {v}")
        lines.append("")
    out_path.write_text("\n".join(lines))


def summary_for_rebuttal(summary_df: pd.DataFrame, decision_df: pd.DataFrame, out_path):
    best_row = summary_df.loc[summary_df["VSC_mean"].idxmax()]
    lines = [
        "# Summary for Rebuttal",
        "",
        f"- Largest VSC observed at budget ${best_row['budget']}M: "
        f"{best_row['VSC_mean'] / 10:.3f} GW "
        f"({100 * best_row['VSC_mean'] / best_row['VSS']:.1f}% of VSS).",
        f"- Decorrelated-model in-sample misestimation and overlap by budget:",
    ]
    for _, r in decision_df.iterrows():
        lines.append(f"  - Budget ${r['budget']}M: Jaccard overlap = {r['jaccard_mean']:.3f}")
    out_path.write_text("\n".join(lines))
```

- [ ] **Step 2: Wire it together in a `main()` and run against the full results**

```python
# addition to Revision_work/vsc/report.py
def main():
    baseline_df = pd.read_csv(VSC_RESULTS_DIR / "baseline.csv")
    summary_df = pd.read_csv(VSC_RESULTS_DIR / "summary_table.csv")
    solve_dir = VSC_RESULTS_DIR / "decorrelated_solutions"

    figure5_updated(baseline_df, summary_df, VSC_RESULTS_DIR / "figure5_updated")
    decomposition_figure(summary_df, VSC_RESULTS_DIR / "decomposition")

    decision_budgets = [20, 40, 60]
    decision_df = decision_comparison_table(
        baseline_df, solve_dir, decision_budgets, VSC_RESULTS_DIR / "decision_comparison.tex"
    )

    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from utils import prepare_input
    from paths import input_dir_str, INPUT_DIR_16
    input1, _ = prepare_input(input_dir_str(INPUT_DIR_16))

    x_so = {
        int(c.split("__")[1]): baseline_df.set_index("budget").loc[40, c]
        for c in baseline_df.columns if c.startswith("x_SO__")
    }
    solve_csv = pd.read_csv(solve_dir / "solve_decorrelated_results.csv")
    x_ind_by_rep = {
        int(r["replication"]): {int(c.split("__")[1]): r[c] for c in solve_csv.columns if c.startswith("x_IND__")}
        for _, r in solve_csv[solve_csv["budget"] == 40].iterrows()
    }
    freq = selection_frequency(x_ind_by_rep)
    substation_map(input1, x_so, freq, VSC_RESULTS_DIR / "substation_map.png")

    validation_report(solve_dir, baseline_df, VSC_RESULTS_DIR / "validation_report.md")
    summary_for_rebuttal(summary_df, decision_df, VSC_RESULTS_DIR / "summary_for_rebuttal.md")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the report generator (requires Task 10's full run to have produced `raw_results.csv`/`summary_table.csv`)**

Run: `python3 Revision_work/vsc/report.py`
Expected: `vsc_results/` contains `figure5_updated.{pdf,png}`, `decomposition.{pdf,png}`, `decision_comparison.tex`, `substation_map.png`, `validation_report.md`, `summary_for_rebuttal.md`.

- [ ] **Step 4: Review the LaTeX table and rebuttal summary by hand**

Open `vsc_results/decision_comparison.tex` and `vsc_results/summary_for_rebuttal.md` and confirm the numbers are self-consistent with `vsc_results/summary_table.csv` (spot-check one budget's VSC/VSS arithmetic by hand).

- [ ] **Step 5: Commit**

```bash
git add Revision_work/vsc/report.py
git commit -m "vsc: generate figures, tables, validation report, and rebuttal summary"
```

---

### Task 12 (optional): Larger independent-sample robustness check (spec Step 7)

**Files:**
- Create: `Revision_work/vsc/independent_sampling.py`

**Interfaces:**
- Consumes: `baseline.load_config` (Task 4), `main_model.two_stage_model`, `evaluate_decorrelated.evaluate_all` (Task 6, reused as-is since it only depends on `x_IND`-shaped columns), `metrics.compute_metrics` (Task 7).
- Produces: `build_independent_sample_flood_df(input1, filter_col, i_f, n_scenarios, seed) -> pd.DataFrame` (draws each flooded substation's height i.i.d. from its own empirical marginal, `N=100` scenarios); a driver analogous to `run_pilot.py` for `budgets={20,40,60}`, `R=5`.

- [ ] **Step 1: Only start this task after Task 11 is complete and the user has confirmed it's worth running**

Per the spec: "Skip this step if solve times make it impractical, and tell me so." Check the Task 9 pilot's per-solve timing: if a single 16-scenario SO solve already took more than ~10 minutes, a 100-scenario model will be substantially larger (more `z`, `g`, `s`, `theta`, `edge` variables and constraints, all indexed by scenario) and likely impractical within a reasonable session; report this to the user instead of running it.

- [ ] **Step 2: Write the sampler**

```python
# Revision_work/vsc/independent_sampling.py
import numpy as np
import pandas as pd

from decorrelate import flooded_substations


def build_independent_sample_flood_df(input1: pd.DataFrame, filter_col: list, n_scenarios: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    i_f = flooded_substations(input1, filter_col)
    sub_values = input1.groupby("SubNum")[filter_col].first()

    new_cols = [f"max_flood_level_indep_{k}" for k in range(n_scenarios)]
    sampled = pd.DataFrame(0.0, index=sub_values.index, columns=new_cols)
    for sub in i_f:
        marginal = sub_values.loc[sub, filter_col].values
        sampled.loc[sub] = rng.choice(marginal, size=n_scenarios, replace=True)

    out = input1[["SubNum"]].merge(sampled, left_on="SubNum", right_index=True, how="left")
    out.index = input1.index
    return out[new_cols]
```

- [ ] **Step 3: Dry-run a single solve to time it before committing to R=5 x 3 budgets**

Run a single `(seed=1, budget=40)` solve using `build_independent_sample_flood_df` swapped in exactly as `solve_one_replication` does for `build_decorrelated_flood_df`, and time it. If it exceeds a few times the 16-scenario pilot's per-solve time, report to the user and stop per Step 1's instruction rather than running the full 5×3 grid.

- [ ] **Step 4: If proceeding, extend `run_pilot.py`'s pattern for `budgets=[20,40,60]`, `seeds=[1..5]`, and report whether VSC changes materially from the permutation-based result**

- [ ] **Step 5: Commit**

```bash
git add Revision_work/vsc/independent_sampling.py
git commit -m "vsc: add optional larger-N independent-sampling robustness check"
```

---

## Self-Review Notes

- **Spec coverage:** Instructions for Claude (repo inspection) → done in this planning pass, findings folded into Global Constraints and Task 4's `model_params.json` note. Step 1 → Task 4. Step 2 + validation → Task 3. Step 3 → Task 5. Step 4 → Task 6. Step 5 → Task 7. Step 6 → Task 8 + Task 11. Step 7 (optional) → Task 12. Deliverables 1–2 → Task 10. Deliverables 3–8 → Task 11. Computational notes 1–2 → baked into Tasks 5/6 (fixed MIP gap/time limit, warm-start-by-reuse pattern). Computational note 3 (Threads) → Global Constraints + Task 10 Step 1. Computational note 4 (resumability) → Task 5's per-solve CSV append + Task 10's `already_done` skip logic. Computational note 5 (pilot first) → Task 9.
- **Placeholder scan:** the one intentional placeholder (`"dummy_never_used"` in Task 4's first draft) is explicitly called out and removed in that same task's Step 2 — it is not left unresolved.
- **Type consistency:** `x_SO__<SubNum>` / `x_IND__<SubNum>` column naming is used consistently from Task 4 through Task 11's `report.py`. `budget` is always in millions of dollars (multiplied by `1e6` only at the `budget_ref.rhs` assignment, matching the existing notebooks). `metrics.compute_metrics`'s output columns (`VSC`, `VMV`, `VSS`, `VSC_share`, `misestimation`, `misestimation_pct`, `worst_case_gap`, `EVPI`, `vsc_negative_flag`) match what `summarize()` and `report.py` consume.

## Critical Blocker Found During Planning

**`gurobipy` is not installed in any Python environment discovered on this machine** (checked `/usr/bin/python3` and the `/opt/miniconda3` base conda env — both lack `gurobipy` and `pyomo`). Every task from Task 4 onward instantiates `two_stage_model`, which calls `gp.Model()` in its constructor, so **nothing in this pipeline can run — not even reloading existing `.sol` files — until a working, licensed Gurobi installation is confirmed.** Task 1 makes this an explicit, first-class precondition rather than something that fails opaquely deep into Task 4 or 5.
