# Slow-Storm Scenario-Weight Sensitivity: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quantify how moving probability mass from the fastest (speed-25) MEOW scenarios to the slowest (speed-05) ones changes the optimal expected load shed, the hardening plan and the near-optimal long-term budget. Also measure how the uniform, robust and mean-value plans perform under the shifted weights. The results are the quantitative answer to Reviewer 3, comment 1.

**Architecture:**
- Small modules live under `Revision_work/slow_storm/`, following the pattern of `Revision_work/certainty/`.
- **Cheap part.** Each fixed plan (SO, RO, MV and the new SLOW plan) is fixed on the 16-scenario model and re-solved once per budget at MIPGap 1e-4. This gives its 16-vector of per-scenario load shed. Every weighting is then a dot product with that vector.
- **Expensive part.** The only new optimization is the re-solve of SO under the slow weights p^slow (λ = 1). It uses a 12-scenario model with a weighted objective, set without editing `main_model.py`.
- **Testing.** The pure logic (weights, metrics, budget economics, validation) gets plain-assert unit tests. The Gurobi-driving code is validated by the pilot's validation report.

**Tech Stack:** Python 3 at `/opt/miniconda3/bin/python` (it has gurobipy 12.0.3, pandas and matplotlib; pytest is not installed, so test files carry a `__main__` runner), `gurobipy`, `pandas`, `numpy`, `matplotlib`.

**Spec:** [Revision_work/slow_storm_sensitivity_experiment.md](slow_storm_sensitivity_experiment.md)

## Global Constraints

- **Solver settings.** Hold every `config.yaml` entry fixed: `fixed_cost=25000`, `variable_cost=100000`, `mit_coarse=1`, `flexible_generation=True`, `robust_flag=False` (the RO plan loader alone sets `True`), `set_objective='min'`, `reference_bus=313`, `mip_gap=0.005`, `solver_method=2`, `time_limit=21600` (6 h; spec open question 1, default). Load config via `vsc.baseline.load_config(time_limit_override=None)`.
- **Evaluation gap.** Fix-and-resolve evaluation solves use **MIPGap = 1e-4**. All other solves use `mip_gap`.
- **Budget sweep.** Exactly `[0, 10, 20, 30, 40, 50, 60, 70, 80]` ($M). The pilot re-optimizes the SLOW plan only at `[20, 40, 60]`.
- **Weights.** Use λ grid `[0, 0.25, 0.5, 0.75, 1.0]`. The slow-shift weights per direction are speed 05: (1+λ)/16, speeds 10 and 15: 1/16, speed 25: (1−λ)/16. The SLOW plan is re-optimized at λ = 1 only.
- **Budget economics.** γ = 10 storms, T ∈ {6, 12, 24, 48} h, VOLL ∈ {250, 500, 1000, 3000, 5000} $/MWh, and TotalCost(I) = I·1e6 + γ·T·VOLL·100·L(I), with L in raw model units. The near-optimal budget is the argmin over the 9-point grid (spec open question 2, default).
- **Do not edit** `main_model.py`, `config.yaml`, or any checked-in notebook.
- **Loss expression.** Build every loss expression explicitly as `load.sum() − Σ p_k Σ_i s[i,k]`. `getObjective()` drops the constant.
- **Substation keys.** Substation ids are handled as `str` everywhere outside Gurobi. Map to the model's keys with `{str(s): s for s in m.unique_substations}`.
- **Resumability.** Save after every solve (CSV append or JSON cache). Solves run sequentially, because `config.yaml` sets no `Threads`.
- **Units.** Raw objective ÷ 10 = GW, in every table and figure.
- **Ask the user** before running the pilot or the full sweep.

## Review Focus

1. **A robust `.sol` file read into a model.** Robust `.sol` files contain `tau`/`tau_scenario` variables. The loader builds the model with `robust_flag=True` so every name resolves. Pinned by the Task 4 smoke check and by the `validation_checks` row "uniform mean of x_RO == robust_decisions_stochastic_solutions.csv" (Task 3). Both catch a mis-read plan.
2. **Zero-weight scenarios.** At λ = 1 the speed-25 columns must be dropped from the SLOW model. The objective must be renormalized over the 12 remaining scenarios, and a plan evaluated under λ = 1 must give zero weight to speed-25 load shed. Pinned by `test_slow_shift_weights_lambda_one` and `test_weighted_loss_ignores_zero_weight`.
3. **A substation that floods only in speed-25 scenarios.** Under λ = 1 it gets no flood constraint in the SLOW model, and the SLOW plan must never harden it. It must still show up in `substation_changes` as "dropped" if SO hardened it. Pinned by `test_substation_changes_classifies`.
4. **Negative Δ_mis.** If the 6 h re-solve fails to beat the warm-started uniform plan, Δ_mis can come out slightly negative. This must be flagged in validation, not silently clipped. Pinned by `test_validation_flags_slow_not_better_than_so`.
5. **Ties in the budget argmin.** Ties must resolve to the smallest budget, and the curve index must be sorted before taking the argmin. Pinned by `test_near_optimal_budget_ties_pick_smallest`.

---

## File Structure

```
Revision_work/slow_storm/
  slow_paths.py        # sys.path wiring + result/output dirs (reuses certainty/common.py)
  storm_weights.py     # λ-weights, scenario parsing, weighted_loss            (pure)
  slow_metrics.py      # vectors → summary, λ-curves, budget economics,
                       #   validation, substation changes                    (pure)
  slow_plans.py        # SO plans from baseline.csv, RO from rm_16 .sol, MV via EV (cached)
  slow_evaluate.py     # fix-and-resolve → per-scenario 16-vectors (resumable)
  slow_solve.py        # weighted SO re-solve under p^slow (resumable, warm-started)
  slow_report.py       # tables, figures A/B/C, validation_report.md
  run_slow_storm.py    # orchestrator: pilot | full | report {pilot|full}
  tests/test_slow_storm.py

Modify:
  Revision_work/certainty/common.py   # add scenario_subset_input1 (single_scenario_input1 wraps it)
  Revision_work/vsc/baseline.py       # extract mean_value_solutions() from _mean_value_bound

slow_storm_results/                   # untracked output (like vsc_results/, certainty_results/)
  ro_plans.json, mv_plans.json, fixed_plan_vectors.csv   # shared across modes
  pilot/ , full/                      # slow_solves.csv, slow_plan_vectors.csv, solves/, tables, figures
```

---

### Task 0: Commit the pending certainty-experiment work (prerequisite)

The certainty experiment (`Revision_work/certainty/`, its spec, and the `load_config` change in `vsc/baseline.py`) is still uncommitted. Tasks 1–2 modify two of those files. Commit that work first so the two experiments stay in separate commits.

- [ ] **Step 1: Ask the user to approve the commit.** They have not yet answered the earlier question. If they decline, skip the commit steps in this whole plan and leave everything uncommitted.
- [ ] **Step 2: Commit**

```bash
git add Revision_work/certainty/*.py Revision_work/certainty/tests/test_certainty.py \
        Revision_work/single_scenario_certainty_experiment.md Revision_work/vsc/baseline.py
git commit -m "certainty: single-scenario certainty experiment (spec, pipeline, tests)"
```

---

### Task 1: Shared-helper generalizations

**Files:**
- Modify: `Revision_work/certainty/common.py` (`single_scenario_input1`)
- Modify: `Revision_work/vsc/baseline.py` (`_mean_value_bound`)
- Test: `Revision_work/certainty/tests/test_certainty.py`

**Interfaces:**
- Produces: `scenario_subset_input1(input1: pd.DataFrame, scenario_cols: list[str]) -> pd.DataFrame`, which drops all `max*` columns and re-appends `scenario_cols` in the given order. `single_scenario_input1(input1, col)` becomes `scenario_subset_input1(input1, [col])`.
- Produces: `vsc.baseline.mean_value_solutions(model_params: dict, budget_vector: list) -> dict[int, dict]`, mapping budget → {substation (model key): x value from the EV solve}. `_mean_value_bound` keeps its behavior and calls it.

- [ ] **Step 1: Write the failing test** (append to `Revision_work/certainty/tests/test_certainty.py`, before the `__main__` block)

```python
def test_scenario_subset_input1_keeps_order_and_positions():
    from common import scenario_subset_input1
    df = pd.DataFrame({"BusNum": [1], "BusName": ["x"], "SubNum": [7], "SubName": ["p"],
                       "Latitude": [0], "Longitude": [0], "generation_capacity_min": [0],
                       "generation_capacity_max": [1], "load": [5],
                       "max_flood_level_a": [1], "max_flood_level_b": [2], "max_flood_level_c": [3]})
    out = scenario_subset_input1(df, ["max_flood_level_c", "max_flood_level_a"])
    assert list(out.columns)[:9] == list(df.columns)[:9]
    assert [c for c in out.columns if c.startswith("max")] == ["max_flood_level_c", "max_flood_level_a"]
    assert out["max_flood_level_c"].tolist() == [3]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `/opt/miniconda3/bin/python Revision_work/certainty/tests/test_certainty.py`
Expected: `ImportError: cannot import name 'scenario_subset_input1'`

- [ ] **Step 3: Implement.** In `Revision_work/certainty/common.py`, replace `single_scenario_input1` with:

```python
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
```

In `Revision_work/vsc/baseline.py`, split `_mean_value_bound`:

```python
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
```

- [ ] **Step 4: Run all existing tests to verify they pass**

Run: `for t in Revision_work/certainty/tests/*.py Revision_work/vsc/tests/*.py; do /opt/miniconda3/bin/python $t | tail -1; done`
Expected: every file prints `All ... tests passed.`

- [ ] **Step 5: Commit**

```bash
git add Revision_work/certainty/common.py Revision_work/certainty/tests/test_certainty.py Revision_work/vsc/baseline.py
git commit -m "shared: add scenario_subset_input1 and mean_value_solutions helpers"
```

---

### Task 2: Path wiring and slow-shift weights

**Files:**
- Create: `Revision_work/slow_storm/slow_paths.py`
- Create: `Revision_work/slow_storm/storm_weights.py`
- Test: `Revision_work/slow_storm/tests/test_slow_storm.py`

**Interfaces:**
- Produces (`slow_paths`): `SLOW_RESULTS_DIR`, `RM16_OUTPUT_DIR`, `SM16_OUTPUT_DIR`, `CERTAINTY_RESULTS_DIR`, `WAIT_AND_SEE_JSON`, `REPO_ROOT`, `SCENARIO_PREFIX`, and the re-exported helpers `append_row`, `apply_solver_params`, `flood_columns`, `read_rows`, `scenario_subset_input1`, `short_name`.
- Produces (`storm_weights`):
  - `parse_scenario(name: str) -> tuple[str, str, str]`, giving (direction, category, speed). It accepts full column names or short names.
  - `slow_shift_weights(scenarios: list[str], lam: float) -> pd.Series`, indexed by short name and summing to 1.
  - `weighted_loss(vector: pd.Series, weights: pd.Series) -> float`.

- [ ] **Step 1: Write the failing tests** in `Revision_work/slow_storm/tests/test_slow_storm.py`

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from storm_weights import parse_scenario, slow_shift_weights, weighted_loss

DIRS = ["w", "wnw", "nw", "nnw"]
SPEEDS = ["05", "10", "15", "25"]
SCEN = [f"{d}_5_{s}" for d in DIRS for s in SPEEDS]


def test_parse_scenario_accepts_full_and_short_names():
    assert parse_scenario("max_flood_level_wnw_5_25") == ("wnw", "5", "25")
    assert parse_scenario("nw_5_05") == ("nw", "5", "05")


def test_slow_shift_weights_lambda_zero_is_uniform():
    w = slow_shift_weights(SCEN, 0.0)
    assert list(w.index) == SCEN
    assert all(abs(v - 1 / 16) < 1e-12 for v in w)


def test_slow_shift_weights_lambda_one():
    w = slow_shift_weights(["max_flood_level_" + s for s in SCEN], 1.0)
    assert abs(w.sum() - 1) < 1e-12
    assert abs(w["w_5_05"] - 2 / 16) < 1e-12 and w["w_5_25"] == 0
    assert abs(w["nnw_5_10"] - 1 / 16) < 1e-12 and abs(w["nnw_5_15"] - 1 / 16) < 1e-12
    for d in DIRS:  # direction marginals unchanged
        assert abs(w[[f"{d}_5_{s}" for s in SPEEDS]].sum() - 0.25) < 1e-12


def test_slow_shift_weights_partial_lambda():
    w = slow_shift_weights(SCEN, 0.5)
    assert abs(w["wnw_5_05"] - 1.5 / 16) < 1e-12 and abs(w["wnw_5_25"] - 0.5 / 16) < 1e-12


def test_slow_shift_weights_rejects_bad_input():
    for bad_lam in (-0.1, 1.1):
        try:
            slow_shift_weights(SCEN, bad_lam)
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
    try:
        slow_shift_weights([s for s in SCEN if s != "w_5_25"], 1.0)
        raise AssertionError("expected ValueError for missing speed-25 partner")
    except ValueError:
        pass


def test_weighted_loss_ignores_zero_weight():
    vec = pd.Series({s: (100.0 if s.endswith("25") else 1.0) for s in SCEN})
    assert abs(weighted_loss(vec, slow_shift_weights(SCEN, 1.0)) - 1.0) < 1e-12
    assert abs(weighted_loss(vec, slow_shift_weights(SCEN, 0.0)) - (12 + 400) / 16) < 1e-12


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("All slow-storm tests passed.")
```

- [ ] **Step 2: Run to verify it fails**

Run: `/opt/miniconda3/bin/python Revision_work/slow_storm/tests/test_slow_storm.py`
Expected: `ModuleNotFoundError: No module named 'storm_weights'`

- [ ] **Step 3: Implement** `Revision_work/slow_storm/slow_paths.py`

```python
"""sys.path wiring and paths for the slow-storm sensitivity experiment.

Spec: Revision_work/slow_storm_sensitivity_experiment.md. Reuses
Revision_work/certainty/common.py, which in turn puts Revision_work/vsc/ and the
repo root on sys.path. Module names here are prefixed (slow_*, storm_*) so they
never collide with vsc/ or certainty/ modules.
"""
import sys
from pathlib import Path

SLOW_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SLOW_DIR.parent / "certainty"))

from common import (CERTAINTY_RESULTS_DIR, REPO_ROOT, SCENARIO_PREFIX,  # noqa: E402,F401
                    SM16_OUTPUT_DIR, WAIT_AND_SEE_JSON, append_row, apply_solver_params,
                    flood_columns, read_rows, scenario_subset_input1, short_name)

RM16_OUTPUT_DIR = REPO_ROOT / "output" / "rm_16"
SLOW_RESULTS_DIR = REPO_ROOT / "slow_storm_results"
```

and `Revision_work/slow_storm/storm_weights.py`

```python
"""Slow-storm scenario weights (spec: 'Scenario set and weightings').

Within each direction, a fraction lam of the fastest scenario's (speed 25) mass
moves to the slowest (speed 05): p = (1+lam)/n, 1/n, 1/n, (1-lam)/n.
"""
import pandas as pd

from slow_paths import short_name

SLOW_SPEED, FAST_SPEED = "05", "25"


def parse_scenario(name: str) -> tuple:
    direction, category, speed = short_name(name).split("_")
    return direction, category, speed


def slow_shift_weights(scenarios: list, lam: float) -> pd.Series:
    if not 0.0 <= lam <= 1.0:
        raise ValueError(f"lambda must be in [0, 1], got {lam}")
    names = [short_name(s) for s in scenarios]
    speeds_by_dir = {}
    for n in names:
        d, _, sp = parse_scenario(n)
        speeds_by_dir.setdefault(d, []).append(sp)
    for d, speeds in speeds_by_dir.items():
        if speeds.count(SLOW_SPEED) != 1 or speeds.count(FAST_SPEED) != 1:
            raise ValueError(f"direction {d!r} needs exactly one speed-{SLOW_SPEED} "
                             f"and one speed-{FAST_SPEED} scenario, got {speeds}")
    base = 1.0 / len(names)
    weights = {}
    for n in names:
        sp = parse_scenario(n)[2]
        if sp == SLOW_SPEED:
            weights[n] = base * (1 + lam)
        elif sp == FAST_SPEED:
            weights[n] = base * (1 - lam)
        else:
            weights[n] = base
    return pd.Series(weights)


def weighted_loss(vector: pd.Series, weights: pd.Series) -> float:
    """sum_k p_k L(x, k); `vector` is indexed by scenario short name."""
    return float((vector[weights.index].astype(float) * weights).sum())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/opt/miniconda3/bin/python Revision_work/slow_storm/tests/test_slow_storm.py`
Expected: `All slow-storm tests passed.`

- [ ] **Step 5: Commit**

```bash
git add Revision_work/slow_storm/slow_paths.py Revision_work/slow_storm/storm_weights.py Revision_work/slow_storm/tests/test_slow_storm.py
git commit -m "slow_storm: slow-shift scenario weights and path wiring"
```

---

### Task 3: Pure metrics: summary, λ-curves, budget economics, validation, substation changes

**Files:**
- Create: `Revision_work/slow_storm/slow_metrics.py`
- Test: `Revision_work/slow_storm/tests/test_slow_storm.py` (append)

**Interfaces:**
- Consumes: `slow_shift_weights`, `weighted_loss`, `parse_scenario` (Task 2), and `SCENARIO_PREFIX` (Task 2).
- Consumes these data shapes:
  - `vectors_df`: columns `plan ∈ {SO, RO, MV, SLOW}`, `budget`, and `L__<short>` for all 16 scenarios, plus others that are ignored.
  - `slow_df`: columns `budget`, `L_star_slow_solver`, `gap`, `x__<sub>`.
  - `baseline_df`: `certainty_results/baseline.csv` (budget, L_SO_star, L_SO_star_gap, L_SO_xbar, x_SO__<sub>).
- Produces:
  - `plan_vectors(vectors_df, plan) -> pd.DataFrame`: index budget, columns scenario short names.
  - `lambda_curves(vectors_df, lambdas) -> pd.DataFrame`: columns plan, budget, lam, L.
  - `build_summary(vectors_df, slow_df, baseline_df, ro_star: pd.Series, ws_cache: dict) -> pd.DataFrame`: one row per budget.
  - `near_optimal_budget(curve: pd.Series, gamma, restoration_h, voll) -> tuple[int, float]`.
  - `budget_table(summary, gamma, restoration_hours, volls) -> pd.DataFrame`.
  - `validation_checks(summary, curves, ro_uniform_csv: pd.Series, mip_gap) -> pd.DataFrame`: columns check, budget, value, reference, passed.
  - `substation_changes(x_so: dict, x_slow: dict, flood_by_sub: pd.DataFrame) -> pd.DataFrame`.

- [ ] **Step 1: Write the failing tests** (append before `__main__`)

```python
from slow_metrics import (budget_table, build_summary, lambda_curves, near_optimal_budget,
                          substation_changes, validation_checks)


def _vectors():
    rows = []
    # SO: speed-25 scenarios cost 2, others 1; RO: flat 1.5; MV: flat 3; SLOW: 05 costs 0.5, 25 costs 4
    spec = {"SO": lambda s: 2.0 if s.endswith("25") else 1.0,
            "RO": lambda s: 1.5,
            "MV": lambda s: 3.0,
            "SLOW": lambda s: 4.0 if s.endswith("25") else (0.5 if s.endswith("05") else 1.0)}
    for plan, f in spec.items():
        row = {"plan": plan, "budget": 20}
        row.update({f"L__{s}": f(s) for s in SCEN})
        rows.append(row)
    return pd.DataFrame(rows)


def _baseline():
    return pd.DataFrame({"budget": [20], "L_SO_star": [1.25], "L_SO_star_gap": [0.0], "L_SO_xbar": [3.0],
                         "x_SO__1": [3.0], "x_SO__2": [0.0]})


def _slow_df(obj=0.9):
    return pd.DataFrame({"budget": [20], "L_star_slow_solver": [obj], "gap": [0.0],
                         "x__1": [0.0], "x__2": [4.0]})


WS = {"20": {f"max_flood_level_{s}": 0.2 for s in SCEN}}


def test_build_summary_quantities():
    s = build_summary(_vectors(), _slow_df(), _baseline(), pd.Series({20: 1.6}), WS).iloc[0]
    assert abs(s["L0_xSO"] - (12 * 1 + 4 * 2) / 16) < 1e-12        # 1.25
    assert abs(s["L_slow_xSO"] - 1.0) < 1e-12                      # speed-25 weight is 0
    # SLOW under p_slow: 4 dirs x (2/16*0.5 + 2*1/16*1) = 0.75
    assert abs(s["L_star_slow"] - 0.75) < 1e-12
    assert abs(s["delta_mis"] - 0.25) < 1e-12
    assert abs(s["L0_xslow"] - (4 * (0.5 + 1 + 1 + 4)) / 16) < 1e-12
    assert abs(s["delta_rev"] - (s["L0_xslow"] - s["L0_xSO"])) < 1e-12
    assert abs(s["WS_slow"] - 0.2) < 1e-12
    assert s["max_xRO"] == 1.5 and s["L_RO_star"] == 1.6


def test_build_summary_without_slow_rows_gives_nan():
    v = _vectors()
    s = build_summary(v[v["plan"] != "SLOW"], _slow_df().iloc[0:0], _baseline(), pd.Series({20: 1.6}), WS).iloc[0]
    assert pd.isna(s["L_star_slow"]) and pd.isna(s["delta_mis"])


def test_lambda_curves_interpolate():
    c = lambda_curves(_vectors(), [0.0, 0.5, 1.0]).set_index(["plan", "lam"])["L"]
    assert abs(c[("SO", 0.0)] - 1.25) < 1e-12 and abs(c[("SO", 1.0)] - 1.0) < 1e-12
    assert abs(c[("SO", 0.5)] - 1.125) < 1e-12  # linear in lambda
    assert abs(c[("RO", 0.5)] - 1.5) < 1e-12


def test_near_optimal_budget_picks_min_total_cost():
    curve = pd.Series({20: 1.0, 0: 5.0, 10: 2.0})  # unsorted on purpose
    # multiplier = 10*12*1000*100 = 12e6 $ per raw unit
    b, cost = near_optimal_budget(curve, gamma=10, restoration_h=12, voll=1000)
    assert b == 20 and abs(cost - (20e6 + 12e6)) < 1e-6


def test_near_optimal_budget_ties_pick_smallest():
    curve = pd.Series({0: 1.0, 10: 0.5})
    # multiplier 20e6 -> cost(0) = 20e6, cost(10) = 10e6 + 10e6 = 20e6
    b, _ = near_optimal_budget(curve, gamma=10, restoration_h=20, voll=1000)
    assert b == 0


def test_budget_table_regret_of_uniform_budget():
    summ = pd.DataFrame({"budget": [0, 10], "L_SO_star": [5.0, 1.0], "L0_xSO": [5.0, 1.0],
                         "L_star_slow": [6.0, 0.5], "L_slow_xSO": [6.0, 2.0]})
    t = budget_table(summ, gamma=10, restoration_hours=[12], volls=[1000]).iloc[0]
    assert t["I_uniform"] == 10 and t["I_slow"] == 10
    assert abs(t["cost_uniform_plan_under_slow"] - (10e6 + 12e6 * 2.0)) < 1e-6
    assert abs(t["regret_usd"] - (12e6 * 2.0 - 12e6 * 0.5)) < 1e-6


def test_validation_flags_slow_not_better_than_so():
    v = _vectors()
    v.loc[v["plan"] == "SLOW", [f"L__{s}" for s in SCEN]] = 1.2  # SLOW worse than SO under p_slow
    summ = build_summary(v, _slow_df(obj=1.2), _baseline(), pd.Series({20: 1.6}), WS)
    checks = validation_checks(summ, lambda_curves(v, [0.0, 1.0]), pd.Series({20: 1.5}), mip_gap=0.005)
    row = checks[checks["check"] == "L*_slow <= L_slow(x_SO)"].iloc[0]
    assert not row["passed"]


def test_validation_passes_on_consistent_data():
    v = _vectors()
    summ = build_summary(v, _slow_df(obj=0.75), _baseline(), pd.Series({20: 1.6}), WS)
    checks = validation_checks(summ, lambda_curves(v, [0.0, 0.5, 1.0]), pd.Series({20: 1.5}), mip_gap=0.005)
    failed = checks[~checks["passed"]]
    # MV flat 3.0 == L_SO_xbar 3.0; RO mean 1.5 == csv 1.5; RO max 1.5 <= 1.6
    assert failed.empty, failed.to_string()


def test_substation_changes_classifies():
    flood = pd.DataFrame({s: [0.0, 6.0, 2.0] if s.endswith("05") else [3.0, 0.0, 2.0] for s in SCEN},
                         index=["1", "2", "3"])
    out = substation_changes({"1": 3, "2": 0, "3": 2}, {"1": 0, "2": 4, "3": 2}, flood).set_index("substation")
    assert out.loc["1", "change"] == "dropped" and out.loc["2", "change"] == "added"
    assert "3" not in out.index
    assert out.loc["2", "mean_flood_05"] == 6.0 and out.loc["2", "mean_flood_25"] == 0.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `/opt/miniconda3/bin/python Revision_work/slow_storm/tests/test_slow_storm.py`
Expected: `ModuleNotFoundError: No module named 'slow_metrics'`

- [ ] **Step 3: Implement** `Revision_work/slow_storm/slow_metrics.py`

```python
"""Pure metrics for the slow-storm experiment (spec: Metrics A-C, Validation).

Raw model units throughout (divide by 10 for GW). A plan's expected load shed
under any weighting is a dot product with its per-scenario vector L(x, k).
Comparisons use the 1e-4-gap evaluated vectors on both sides (L0_xSO, not the
baseline's 0.5%-gap incumbent), so Delta_mis and Delta_rev are apples to apples.
"""
import math

import numpy as np
import pandas as pd

from slow_paths import SCENARIO_PREFIX
from storm_weights import parse_scenario, slow_shift_weights, weighted_loss

ABS_FLOOR = 1e-4
MW_PER_UNIT = 100


def plan_vectors(vectors_df: pd.DataFrame, plan: str) -> pd.DataFrame:
    cols = [c for c in vectors_df.columns if c.startswith("L__")]
    sel = vectors_df[vectors_df["plan"] == plan].set_index("budget")[cols]
    sel.columns = [c[len("L__"):] for c in cols]
    return sel.sort_index()


def lambda_curves(vectors_df: pd.DataFrame, lambdas: list) -> pd.DataFrame:
    rows = []
    for plan in sorted(vectors_df["plan"].unique()):
        vecs = plan_vectors(vectors_df, plan)
        for lam in lambdas:
            w = slow_shift_weights(list(vecs.columns), lam)
            for budget, vec in vecs.iterrows():
                rows.append({"plan": plan, "budget": budget, "lam": lam, "L": weighted_loss(vec, w)})
    return pd.DataFrame(rows)


def build_summary(vectors_df, slow_df, baseline_df, ro_star: pd.Series, ws_cache: dict) -> pd.DataFrame:
    so, ro, mv = (plan_vectors(vectors_df, p) for p in ("SO", "RO", "MV"))
    has_slow_vec = (vectors_df["plan"] == "SLOW").any()
    slow = plan_vectors(vectors_df, "SLOW") if has_slow_vec else pd.DataFrame()
    solver = slow_df.set_index("budget") if len(slow_df) else pd.DataFrame()
    w0 = slow_shift_weights(list(so.columns), 0.0)
    w1 = slow_shift_weights(list(so.columns), 1.0)
    base = baseline_df.set_index("budget")

    rows = []
    for b in so.index:
        r = {
            "budget": b,
            "L_SO_star": base.loc[b, "L_SO_star"],
            "L_SO_star_gap": base.loc[b, "L_SO_star_gap"],
            "L_SO_xbar": base.loc[b, "L_SO_xbar"],
            "L0_xSO": weighted_loss(so.loc[b], w0),
            "L_slow_xSO": weighted_loss(so.loc[b], w1),
            "L0_xRO": weighted_loss(ro.loc[b], w0),
            "L_slow_xRO": weighted_loss(ro.loc[b], w1),
            "max_xRO": float(ro.loc[b].max()),
            "L_RO_star": float(ro_star[b]),
            "L0_xMV": weighted_loss(mv.loc[b], w0),
            "L_slow_xMV": weighted_loss(mv.loc[b], w1),
            "WS_slow": sum(w1[s] * ws_cache[str(int(b))][SCENARIO_PREFIX + s] for s in w1.index),
        }
        have = b in slow.index and b in solver.index
        r["L_star_slow"] = weighted_loss(slow.loc[b], w1) if have else np.nan
        r["L0_xslow"] = weighted_loss(slow.loc[b], w0) if have else np.nan
        r["L_star_slow_solver"] = solver.loc[b, "L_star_slow_solver"] if have else np.nan
        r["slow_gap"] = solver.loc[b, "gap"] if have else np.nan
        rows.append(r)

    s = pd.DataFrame(rows)
    s["delta_mis"] = s["L_slow_xSO"] - s["L_star_slow"]
    s["delta_mis_pct"] = 100 * s["delta_mis"] / s["L_star_slow"].where(s["L_star_slow"].abs() > ABS_FLOOR)
    s["delta_rev"] = s["L0_xslow"] - s["L0_xSO"]
    s["risk_shift"] = s["L_star_slow"] - s["L0_xSO"]
    return s


def near_optimal_budget(curve: pd.Series, gamma: float, restoration_h: float, voll: float) -> tuple:
    """argmin over the budget grid of I*1e6 + gamma*T*VOLL*100*L(I); ties -> smallest I."""
    curve = curve.sort_index()
    mult = gamma * restoration_h * voll * MW_PER_UNIT
    cost = pd.Series(curve.index.to_numpy(dtype=float) * 1e6, index=curve.index) + mult * curve
    best = cost.idxmin()  # first occurrence = smallest budget on ties
    return int(best), float(cost.loc[best])


def budget_table(summary: pd.DataFrame, gamma: float, restoration_hours: list, volls: list) -> pd.DataFrame:
    """Near-optimal budget under uniform vs slow weights, and the regret of using
    the uniform-optimal budget (and its SO plan) when storms are actually slower."""
    s = summary.set_index("budget").sort_index()
    rows = []
    for T in restoration_hours:
        for voll in volls:
            mult = gamma * T * voll * MW_PER_UNIT
            i_uni, cost_uni = near_optimal_budget(s["L0_xSO"], gamma, T, voll)
            i_slow, cost_slow = near_optimal_budget(s["L_star_slow"], gamma, T, voll)
            cost_uni_under_slow = i_uni * 1e6 + mult * s.loc[i_uni, "L_slow_xSO"]
            rows.append({"restoration_h": T, "voll": voll,
                         "I_uniform": i_uni, "cost_uniform": cost_uni,
                         "I_slow": i_slow, "cost_slow": cost_slow,
                         "cost_uniform_plan_under_slow": cost_uni_under_slow,
                         "regret_usd": cost_uni_under_slow - cost_slow})
    return pd.DataFrame(rows)


def validation_checks(summary: pd.DataFrame, curves: pd.DataFrame, ro_uniform_csv: pd.Series,
                      mip_gap: float) -> pd.DataFrame:
    rows = []

    def add(check, budget, value, reference, passed):
        rows.append({"check": check, "budget": budget, "value": value,
                     "reference": reference, "passed": bool(passed)})

    for _, r in summary.iterrows():
        b = r["budget"]
        tol_so = max(r["L_SO_star_gap"], mip_gap) * abs(r["L_SO_star"]) + ABS_FLOOR
        add("uniform mean of x_SO == L*_SO", b, r["L0_xSO"], r["L_SO_star"],
            abs(r["L0_xSO"] - r["L_SO_star"]) <= tol_so)
        ref = float(ro_uniform_csv[b])  # 2-decimal CSV: allow rounding
        add("uniform mean of x_RO == robust_decisions_stochastic_solutions.csv", b, r["L0_xRO"], ref,
            abs(r["L0_xRO"] - ref) <= mip_gap * abs(ref) + 0.006)
        add("max_k L(x_RO,k) <= L*_RO", b, r["max_xRO"], r["L_RO_star"],
            r["max_xRO"] <= r["L_RO_star"] * (1 + mip_gap) + ABS_FLOOR)
        add("uniform mean of x_MV == L_SO(x_bar)", b, r["L0_xMV"], r["L_SO_xbar"],
            abs(r["L0_xMV"] - r["L_SO_xbar"]) <= mip_gap * abs(r["L_SO_xbar"]) + ABS_FLOOR)
        if not math.isnan(r["L_star_slow"]):
            tol = max(r["slow_gap"], mip_gap) * abs(r["L_star_slow"]) + ABS_FLOOR
            add("WS_slow <= L*_slow", b, r["WS_slow"], r["L_star_slow"], r["WS_slow"] <= r["L_star_slow"] + tol)
            add("L*_slow <= L_slow(x_SO)", b, r["L_star_slow"], r["L_slow_xSO"],
                r["L_star_slow"] <= r["L_slow_xSO"] + tol)
            add("L*_slow <= L_slow(x_MV)", b, r["L_star_slow"], r["L_slow_xMV"],
                r["L_star_slow"] <= r["L_slow_xMV"] + tol)
            add("solver objective == evaluated L_slow(x_slow)", b, r["L_star_slow_solver"], r["L_star_slow"],
                abs(r["L_star_slow_solver"] - r["L_star_slow"]) <= tol)

    ro_star = summary.set_index("budget")["L_RO_star"]
    for _, c in curves[curves["plan"] == "RO"].iterrows():
        bound = ro_star[c["budget"]]
        add(f"L_lambda(x_RO) <= L*_RO (lambda={c['lam']})", c["budget"], c["L"], bound,
            c["L"] <= bound * (1 + mip_gap) + ABS_FLOOR)
    return pd.DataFrame(rows)


def substation_changes(x_so: dict, x_slow: dict, flood_by_sub: pd.DataFrame) -> pd.DataFrame:
    """Substations whose hardening differs between x_SO and x_slow, with their mean
    flood height (ft) over the speed-05 and speed-25 scenarios."""
    slow_cols = [c for c in flood_by_sub.columns if parse_scenario(c)[2] == "05"]
    fast_cols = [c for c in flood_by_sub.columns if parse_scenario(c)[2] == "25"]
    rows = []
    for sub in sorted(set(x_so) | set(x_slow), key=str):
        a, b = round(x_so.get(sub, 0)), round(x_slow.get(sub, 0))
        if a == b:
            continue
        rows.append({
            "substation": sub, "x_SO": a, "x_slow": b,
            "change": "added" if a == 0 else ("dropped" if b == 0 else "height"),
            "mean_flood_05": float(flood_by_sub.loc[sub, slow_cols].mean()) if sub in flood_by_sub.index else np.nan,
            "mean_flood_25": float(flood_by_sub.loc[sub, fast_cols].mean()) if sub in flood_by_sub.index else np.nan,
        })
    return pd.DataFrame(rows, columns=["substation", "x_SO", "x_slow", "change", "mean_flood_05", "mean_flood_25"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/opt/miniconda3/bin/python Revision_work/slow_storm/tests/test_slow_storm.py`
Expected: `All slow-storm tests passed.`

- [ ] **Step 5: Commit**

```bash
git add Revision_work/slow_storm/slow_metrics.py Revision_work/slow_storm/tests/test_slow_storm.py
git commit -m "slow_storm: summary, lambda curves, budget economics, validation metrics"
```

---

### Task 4: Plan loaders and per-scenario evaluation (Gurobi)

**Files:**
- Create: `Revision_work/slow_storm/slow_plans.py`
- Create: `Revision_work/slow_storm/slow_evaluate.py`

**Interfaces:**
- Consumes: `vsc.baseline.mean_value_solutions` (Task 1), and `slow_paths` helpers (Task 2).
- Produces:
  - `so_plans(baseline_df) -> dict[int, dict[str, float]]`
  - `ro_plans(model_params, budgets, cache_path) -> dict[int, dict[str, float]]`
  - `mv_plans(model_params, budgets, cache_path) -> dict[int, dict[str, float]]`
  - `evaluate_plans(model_params, plans: dict[str, dict[int, dict[str, float]]], out_csv) -> pd.DataFrame`, with columns plan, budget, L_uniform, eval_time_s, eval_gap, eval_status, and `L__<short>` × 16.
- **Plan shape:** `{budget: {substation_str: x_value}}` everywhere.

- [ ] **Step 1: Implement** `Revision_work/slow_storm/slow_plans.py`

```python
"""First-stage plans to evaluate: SO (from certainty_results/baseline.csv), RO
(from output/rm_16/*.sol) and MV (EV solve). RO and MV are cached as JSON."""
import json
from pathlib import Path

import pandas as pd

from env_check import check_environment
from slow_paths import RM16_OUTPUT_DIR


def so_plans(baseline_df: pd.DataFrame) -> dict:
    subs = [c[len("x_SO__"):] for c in baseline_df.columns if c.startswith("x_SO__")]
    return {int(r["budget"]): {s: float(r[f"x_SO__{s}"]) for s in subs} for _, r in baseline_df.iterrows()}


def _cached(cache_path: Path, budgets: list, compute) -> dict:
    cache = {}
    if cache_path.exists():
        cache = {int(b): plan for b, plan in json.loads(cache_path.read_text()).items()}
    missing = [b for b in budgets if b not in cache]
    if missing:
        cache.update(compute(missing))
        cache_path.write_text(json.dumps({str(b): cache[b] for b in sorted(cache)}, indent=1))
    return {b: cache[b] for b in budgets}


def ro_plans(model_params: dict, budgets: list, cache_path: Path) -> dict:
    def compute(missing):
        check_environment()
        from main_model import two_stage_model

        params = dict(model_params)
        params["robust_flag"] = True  # .sol files carry tau/tau_scenario
        m = two_stage_model(params)
        m.model.setParam("LogToConsole", 0)
        m.model.update()
        out = {}
        for b in missing:
            m.model.read(str(RM16_OUTPUT_DIR / f"{b}M_solution.sol"))
            m.model.update()
            out[b] = {str(s): m.model.getVarByName(f"x[{s}]").Start for s in m.unique_substations}
        m.model.dispose()
        return out

    return _cached(cache_path, budgets, compute)


def mv_plans(model_params: dict, budgets: list, cache_path: Path) -> dict:
    def compute(missing):
        check_environment()
        from baseline import mean_value_solutions

        sols = mean_value_solutions(model_params, missing)
        return {b: {str(s): float(v) for s, v in sols[b].items()} for b in missing}

    return _cached(cache_path, budgets, compute)
```

- [ ] **Step 2: Implement** `Revision_work/slow_storm/slow_evaluate.py`

```python
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
        print(f"[eval] {plan}_{budget}M: uniform={gm.ObjVal:.4f} t={t_eval:.0f}s", flush=True)

    gm.dispose()
    return read_rows(out_csv)
```

- [ ] **Step 3: Smoke-check on one budget (Gurobi; takes seconds).** Write a throwaway script in the scratchpad, not the repo. It loads config, builds `ro_plans` / `mv_plans` for `[60]` into a scratch cache, and runs `evaluate_plans` for `{"SO": so_plans(baseline)[60 only], "RO": ..., "MV": ...}` into a scratch CSV.

Expected:
- the uniform mean of the SO vector ≈ 0.6043 (L\*_SO at $60M);
- the RO uniform mean ≈ the $60M row of `output/rm_16/robust_decisions_stochastic_solutions.csv`;
- the MV uniform mean ≈ 21.152 (`L_SO_xbar` at $60M).

If `ro_plans` raises on the `.sol` read, stop and report the error.

- [ ] **Step 4: Commit**

```bash
git add Revision_work/slow_storm/slow_plans.py Revision_work/slow_storm/slow_evaluate.py
git commit -m "slow_storm: SO/RO/MV plan loaders and per-scenario fix-and-resolve evaluation"
```

---

### Task 5: Weighted SO re-solve under p^slow (Gurobi)

**Files:**
- Create: `Revision_work/slow_storm/slow_solve.py`

**Interfaces:**
- Consumes: `slow_shift_weights` (Task 2), `scenario_subset_input1` (Task 1), and `so_plans` output as warm starts (Task 4).
- Produces: `solve_weighted(model_params, weights: pd.Series, budgets: list, warm_plans: dict[int, dict[str, float]], out_dir: Path) -> pd.DataFrame`. The result has columns budget, L_star_slow_solver, bound, gap, status, solve_time_s, spend, n_hardened, and `x__<sub>`. Results are written to `out_dir/slow_solves.csv`, `.sol` files to `out_dir/solves/slow_<I>M_solution.sol`, and logs next to the `.sol` files.

- [ ] **Step 1: Implement** `Revision_work/slow_storm/slow_solve.py`

```python
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
```

- [ ] **Step 2: Smoke-check at $80M (fast: the baseline solved it in 17 s)** with a throwaway scratchpad script and a scratch `out_dir`.

Expected:
- the first log line reports 12 scenarios, with weights 0.125 on speed 05 and 0.0625 on speeds 10 and 15;
- `L_star_slow_solver` ≈ 0, and the assertion passes.

- [ ] **Step 3: Commit**

```bash
git add Revision_work/slow_storm/slow_solve.py
git commit -m "slow_storm: weighted SO re-solve under slow-storm weights"
```

---

### Task 6: Report (tables, figures A/B/C, validation report)

**Files:**
- Create: `Revision_work/slow_storm/slow_report.py`

**Interfaces:**
- Consumes: everything in Task 3, plus `certainty_report._latex_table` and `certainty_metrics.parse_gurobi_log` (both existing), and `vsc/decisions.py`.
- Produces: `build_report(out_dir, model_params, baseline_df, vectors_df, slow_df) -> tuple[summary, checks]`. It writes these files:
  - tables: `summary.csv`, `summary_table.tex`, `lambda_curves.csv`, `budget_table.csv`, `decision_comparison.tex`, `substation_changes.csv`, `validation_report.md`;
  - figures, each as `.pdf` and `.png`: `fig_a_slow_bounds`, `fig_b_lambda_sensitivity`, `fig_c_budget` (only when the SLOW curve covers all 9 budgets).

- [ ] **Step 1: Implement** `Revision_work/slow_storm/slow_report.py`

```python
"""Deliverables of the slow-storm spec: tables, figures A/B/C, validation report.
SUMMARY.md is written by hand from these outputs."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from certainty_metrics import parse_gurobi_log  # noqa: E402
from certainty_report import _latex_table  # noqa: E402
from slow_metrics import (budget_table, build_summary, lambda_curves, substation_changes,  # noqa: E402
                          validation_checks)
from slow_paths import RM16_OUTPUT_DIR, WAIT_AND_SEE_JSON, flood_columns, short_name  # noqa: E402

GW = 10
LAMBDAS = [0.0, 0.25, 0.5, 0.75, 1.0]
ALL_BUDGETS = [0, 10, 20, 30, 40, 50, 60, 70, 80]
PANEL_BUDGETS = [20, 40, 60]
GAMMA, RESTORATION_HOURS, VOLLS = 10, [6, 12, 24, 48], [250, 500, 1000, 3000, 5000]
# manuscript colors (Bounds.ipynb, Robust_performance.ipynb) + certainty pink for the re-optimized plan
C = {"slow": "#cc79a7", "so": "#0072b2", "ro": "#40B0A6", "ro_star": "#DC3220", "mv": "#009e73", "ws": "#d55e00"}


def _inputs(model_params, budgets):
    ro_star = pd.Series({b: parse_gurobi_log(RM16_OUTPUT_DIR / f"{b}M")[0] for b in budgets})
    ro_csv = pd.read_csv(RM16_OUTPUT_DIR / "robust_decisions_stochastic_solutions.csv",
                         encoding="utf-8-sig").set_index("budget").iloc[:, 0]
    with open(WAIT_AND_SEE_JSON) as f:
        ws_cache = json.load(f)
    input1 = model_params["input1"]
    cols = flood_columns(input1)
    flood = input1.groupby("SubNum")[cols].first()
    flood.index = flood.index.astype(str)
    flood.columns = [short_name(c) for c in cols]
    return ro_star, ro_csv, ws_cache, flood


def _plot_fig_a(out_dir, s):
    b = s["budget"]
    fig, ax = plt.subplots(figsize=(4.4, 4.2))
    ax.plot(b, s["L_slow_xMV"] / GW, marker="o", color=C["mv"], label="Mean value plan")
    ax.plot(b, s["L_slow_xRO"] / GW, marker="^", color=C["ro"], label="Robust plan")
    ax.plot(b, s["L_RO_star"] / GW, linestyle="--", color=C["ro_star"], label="RO objective (bound)")
    ax.plot(b, s["L_slow_xSO"] / GW, marker="o", color=C["so"], label="Stochastic plan (uniform)")
    have = s["L_star_slow"].notna()
    ax.plot(b[have], s.loc[have, "L_star_slow"] / GW, marker="s", color=C["slow"],
            label="Stochastic plan (re-optimized, slow)")
    ax.plot(b, s["WS_slow"] / GW, marker="o", color=C["ws"], label="Wait-and-see")
    ax.set_xlabel("Budget in Millions ($)", fontsize=11)
    ax.set_ylabel("Expected load-shed under slow weights (GW)", fontsize=10)
    ax.set_ylim(-0.25, 6)
    ax.legend(loc=1, prop={"size": 8}, frameon=False)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"fig_a_slow_bounds.{ext}", dpi=200)
    plt.close(fig)


def _plot_fig_b(out_dir, s, curves):
    budgets = [b for b in PANEL_BUDGETS if b in set(s["budget"])]
    fig, axes = plt.subplots(1, len(budgets), figsize=(3.2 * len(budgets), 3.4), sharey=False)
    axes = [axes] if len(budgets) == 1 else axes
    srow = s.set_index("budget")
    for ax, b in zip(axes, budgets):
        for plan, color, marker, label in (("SO", C["so"], "o", "Stochastic plan (uniform)"),
                                           ("RO", C["ro"], "^", "Robust plan")):
            c = curves[(curves["plan"] == plan) & (curves["budget"] == b)].sort_values("lam")
            ax.plot(c["lam"], c["L"] / GW, marker=marker, color=color, label=label)
        ax.axhline(srow.loc[b, "L_RO_star"] / GW, linestyle="--", color=C["ro_star"], label="RO objective (bound)")
        if pd.notna(srow.loc[b, "L_star_slow"]):
            ax.plot([1.0], [srow.loc[b, "L_star_slow"] / GW], marker="s", color=C["slow"], linestyle="none",
                    markersize=8, label="Re-optimized at λ=1")
        ax.set_title(f"Budget ${b}M", fontsize=10)
        ax.set_xlabel("λ (share of speed-25 mass moved to speed-05)", fontsize=8)
    axes[0].set_ylabel("Expected load-shed (GW)")
    axes[0].legend(prop={"size": 7}, frameon=False)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"fig_b_lambda_sensitivity.{ext}", dpi=200)
    plt.close(fig)


def _plot_fig_c(out_dir, bt):
    fig, axes = plt.subplots(1, len(RESTORATION_HOURS), figsize=(3 * len(RESTORATION_HOURS), 3.2), sharey=True)
    for ax, T in zip(axes, RESTORATION_HOURS):
        t = bt[bt["restoration_h"] == T]
        ax.plot(range(len(VOLLS)), t["I_uniform"], marker="o", color=C["so"], label="Uniform weights")
        ax.plot(range(len(VOLLS)), t["I_slow"], marker="s", color=C["slow"], linestyle="--", label="Slow weights")
        ax.set_xticks(range(len(VOLLS)), VOLLS, fontsize=8)
        ax.set_title(f"Restoration time {T} h", fontsize=10)
        ax.set_xlabel("VOLL ($/MWh)", fontsize=9)
    axes[0].set_ylabel("Near-optimal budget ($M)")
    axes[0].legend(prop={"size": 8}, frameon=False)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"fig_c_budget.{ext}", dpi=200)
    plt.close(fig)


def _tables(out_dir, s):
    f = lambda v: "--" if pd.isna(v) else f"{v / GW:.3f}"  # noqa: E731
    pct = lambda v: "--" if pd.isna(v) else f"{v:.0f}\\%"  # noqa: E731
    t = pd.DataFrame({
        "Budget (\\$M)": s["budget"].astype(int),
        "$L^*_{SO}$": s["L0_xSO"].map(f),
        "$L^*_{slow}$": s["L_star_slow"].map(f),
        "$L_{slow}(x_{SO})$": s["L_slow_xSO"].map(f),
        "$\\Delta_{mis}$": [f"{f(a)} ({pct(b)})" if pd.notna(a) else "--" for a, b in
                            zip(s["delta_mis"], s["delta_mis_pct"])],
        "$L_{0}(x_{slow})$": s["L0_xslow"].map(f),
        "$L_{slow}(x_{RO})$": s["L_slow_xRO"].map(f),
        "$L^*_{RO}$": s["L_RO_star"].map(f),
        "$WS_{slow}$": s["WS_slow"].map(f),
    })
    (out_dir / "summary_table.tex").write_text(_latex_table(
        t, "Expected load shed (GW) when speed-25 probability mass moves to speed-05 scenarios.",
        "tab:slow_storm_summary"))


def _decisions(out_dir, baseline_df, slow_df, flood):
    from decisions import budget_allocation, jaccard_index, mean_abs_height_diff

    if slow_df.empty:
        return pd.Series(dtype=float)
    subs = [c[len("x_SO__"):] for c in baseline_df.columns if c.startswith("x_SO__")]
    rows, changes, jac = [], [], {}
    for _, r in slow_df.sort_values("budget").iterrows():
        b = int(r["budget"])
        base = baseline_df[baseline_df["budget"] == b].iloc[0]
        x_so = {s: float(base[f"x_SO__{s}"]) for s in subs}
        x_sl = {s: float(r[f"x__{s}"]) for s in subs}
        jac[b] = jaccard_index(x_so, x_sl)
        a_so, a_sl = budget_allocation(x_so), budget_allocation(x_sl)
        diff = mean_abs_height_diff(x_so, x_sl)
        rows.append({"Budget (\\$M)": b, "SO hardened": a_so["n_hardened"], "slow hardened": a_sl["n_hardened"],
                     "SO mean height": f"{a_so['mean_height']:.2f}", "slow mean height": f"{a_sl['mean_height']:.2f}",
                     "Jaccard": f"{jac[b]:.2f}", "mean abs height diff": "--" if pd.isna(diff) else f"{diff:.2f}"})
        ch = substation_changes(x_so, x_sl, flood)
        ch.insert(0, "budget", b)
        changes.append(ch)
    (out_dir / "decision_comparison.tex").write_text(_latex_table(
        pd.DataFrame(rows), "Hardening plans under uniform vs slow-storm weights.", "tab:slow_storm_decisions"))
    pd.concat(changes).to_csv(out_dir / "substation_changes.csv", index=False)
    return pd.Series(jac)


def _validation_report(out_dir, checks, s, bt):
    L = ["# Validation report: slow-storm sensitivity", ""]
    bad = checks[~checks["passed"]]
    L.append(f"{len(checks) - len(bad)}/{len(checks)} checks passed.")
    L += ["", "## Failed checks", "", "None." if bad.empty else "```\n" + bad.to_string(index=False) + "\n```"]
    L += ["", "## All checks", "", "```", checks.to_string(index=False), "```"]
    L += ["", "## Summary (raw units; divide by 10 for GW)", "", "```", s.to_string(index=False), "```"]
    if bt is not None:
        L += ["", "## Near-optimal budget", "", "```", bt.to_string(index=False), "```"]
    (out_dir / "validation_report.md").write_text("\n".join(L) + "\n")


def build_report(out_dir: Path, model_params: dict, baseline_df, vectors_df, slow_df):
    budgets = sorted(int(b) for b in vectors_df.loc[vectors_df["plan"] == "SO", "budget"].unique())
    ro_star, ro_csv, ws_cache, flood = _inputs(model_params, budgets)
    s = build_summary(vectors_df, slow_df, baseline_df, ro_star, ws_cache)
    curves = lambda_curves(vectors_df[vectors_df["plan"] != "SLOW"], LAMBDAS)
    checks = validation_checks(s, curves, ro_csv, model_params["mip_gap"])
    jac = _decisions(out_dir, baseline_df, slow_df, flood)
    s["jaccard_slow_vs_so"] = s["budget"].map(jac)
    s.to_csv(out_dir / "summary.csv", index=False)
    curves.to_csv(out_dir / "lambda_curves.csv", index=False)
    _tables(out_dir, s)
    _plot_fig_a(out_dir, s)
    _plot_fig_b(out_dir, s, curves)
    bt = None
    if s["L_star_slow"].notna().sum() == len(ALL_BUDGETS):
        bt = budget_table(s, GAMMA, RESTORATION_HOURS, VOLLS)
        bt.to_csv(out_dir / "budget_table.csv", index=False)
        _plot_fig_c(out_dir, bt)
    _validation_report(out_dir, checks, s, bt)
    return s, checks
```

- [ ] **Step 2: Commit**

```bash
git add Revision_work/slow_storm/slow_report.py
git commit -m "slow_storm: tables, figures A/B/C and validation report"
```

---

### Task 7: Orchestrator and pilot run

**Files:**
- Create: `Revision_work/slow_storm/run_slow_storm.py`

**Interfaces:**
- Consumes: Tasks 2–6, and `certainty_baseline.get_baseline` (existing; `certainty_results/baseline.csv` already covers all 9 budgets).
- CLI: `/opt/miniconda3/bin/python Revision_work/slow_storm/run_slow_storm.py {pilot|full|report pilot|report full}`.

- [ ] **Step 1: Implement** `Revision_work/slow_storm/run_slow_storm.py`

```python
"""Orchestrator for the slow-storm sensitivity experiment.

    /opt/miniconda3/bin/python Revision_work/slow_storm/run_slow_storm.py pilot
    /opt/miniconda3/bin/python Revision_work/slow_storm/run_slow_storm.py full
    /opt/miniconda3/bin/python Revision_work/slow_storm/run_slow_storm.py report {pilot|full}

Fixed-plan vectors (SO/RO/MV, all budgets) are shared by both modes. Only the
re-optimized SLOW plan differs: pilot re-solves $20M/$40M/$60M, full all 9.
Every solve is appended as it finishes, so rerunning resumes.
"""
import sys
import time

import pandas as pd

from slow_paths import CERTAINTY_RESULTS_DIR, SLOW_RESULTS_DIR, flood_columns, read_rows

ALL_BUDGETS = [0, 10, 20, 30, 40, 50, 60, 70, 80]
PILOT_SLOW_BUDGETS = [20, 40, 60]


def _slow_plans(slow_df: pd.DataFrame) -> dict:
    subs = [c[len("x__"):] for c in slow_df.columns if c.startswith("x__")]
    return {int(r["budget"]): {s: float(r[f"x__{s}"]) for s in subs} for _, r in slow_df.iterrows()}


def run(mode: str):
    from baseline import load_config
    from certainty_baseline import get_baseline
    from slow_evaluate import evaluate_plans
    from slow_plans import mv_plans, ro_plans, so_plans
    from slow_report import build_report
    from slow_solve import solve_weighted
    from storm_weights import slow_shift_weights

    out_dir = SLOW_RESULTS_DIR / mode
    out_dir.mkdir(parents=True, exist_ok=True)
    model_params = load_config(time_limit_override=None)  # config.yaml's 6 h

    t0 = time.time()
    baseline_df = get_baseline(model_params, ALL_BUDGETS, CERTAINTY_RESULTS_DIR / "baseline.csv")
    plans = {"SO": so_plans(baseline_df),
             "RO": ro_plans(model_params, ALL_BUDGETS, SLOW_RESULTS_DIR / "ro_plans.json"),
             "MV": mv_plans(model_params, ALL_BUDGETS, SLOW_RESULTS_DIR / "mv_plans.json")}
    fixed = evaluate_plans(model_params, plans, SLOW_RESULTS_DIR / "fixed_plan_vectors.csv")
    print(f"[{mode}] fixed-plan vectors ready ({time.time() - t0:.0f}s)", flush=True)

    weights = slow_shift_weights(flood_columns(model_params["input1"]), 1.0)
    budgets = PILOT_SLOW_BUDGETS if mode == "pilot" else ALL_BUDGETS
    t0 = time.time()
    slow_df = solve_weighted(model_params, weights, budgets, plans["SO"], out_dir)
    print(f"[{mode}] slow re-solves done ({time.time() - t0:.0f}s)", flush=True)

    slow_vec = evaluate_plans(model_params, {"SLOW": _slow_plans(slow_df)}, out_dir / "slow_plan_vectors.csv")
    vectors = pd.concat([fixed, slow_vec], ignore_index=True)
    s, checks = build_report(out_dir, model_params, baseline_df, vectors, slow_df)
    print(s.to_string(index=False))
    print(f"[{mode}] validation: {int(checks['passed'].sum())}/{len(checks)} checks passed", flush=True)


def report_only(mode: str):
    from baseline import load_config
    from slow_report import build_report

    out_dir = SLOW_RESULTS_DIR / mode
    model_params = load_config(time_limit_override=None)
    baseline_df = pd.read_csv(CERTAINTY_RESULTS_DIR / "baseline.csv")
    slow_df = read_rows(out_dir / "slow_solves.csv")
    vectors = pd.concat([read_rows(SLOW_RESULTS_DIR / "fixed_plan_vectors.csv"),
                         read_rows(out_dir / "slow_plan_vectors.csv")], ignore_index=True)
    s, checks = build_report(out_dir, model_params, baseline_df, vectors, slow_df)
    print(s.to_string(index=False))
    print(f"[report {mode}] validation: {int(checks['passed'].sum())}/{len(checks)} checks passed")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 1 and args[0] in ("pilot", "full"):
        run(args[0])
    elif len(args) == 2 and args[0] == "report" and args[1] in ("pilot", "full"):
        report_only(args[1])
    else:
        sys.exit(__doc__)
```

- [ ] **Step 2: Run all unit tests**

Run: `for t in Revision_work/slow_storm/tests/*.py Revision_work/certainty/tests/*.py Revision_work/vsc/tests/*.py; do /opt/miniconda3/bin/python $t | tail -1; done`
Expected: every file prints `All ... tests passed.`

- [ ] **Step 3: Commit**

```bash
git add Revision_work/slow_storm/run_slow_storm.py
git commit -m "slow_storm: pilot/full/report orchestrator"
```

- [ ] **Step 4: Ask the user before starting the pilot.** Warn them that the $20M re-solve can take up to 6 h: the uniform baseline hit the 6 h cap there. The whole pilot can take up to about 18 h.

- [ ] **Step 5: Run the pilot in the background** and stream progress with a Monitor that emits once a minute on `[slow]` / `[eval]` / `[pilot]` lines and on any `Traceback|Error|assert`:

```bash
/opt/miniconda3/bin/python -u Revision_work/slow_storm/run_slow_storm.py pilot > slow_storm_results/pilot_run.log 2>&1
```

- [ ] **Step 6: Review the pilot's `validation_report.md` and figures.** Report to the user:
  - the checks passed;
  - the solve time and final gap of each re-solve;
  - Δ_mis and Δ_rev at $20M, $40M and $60M;
  - whether `max_xRO <= L*_RO` holds at every budget.

  Then ask whether to run the full sweep.

---

### Task 8: Full sweep and summary

- [ ] **Step 1: Run the full sweep** after the user approves. The pilot's three re-solves are **not** reused, because `full/` is a separate directory. To reuse them, copy `slow_storm_results/pilot/slow_solves.csv` and `solves/` into `slow_storm_results/full/` before starting. The resume logic then skips those budgets.

```bash
/opt/miniconda3/bin/python -u Revision_work/slow_storm/run_slow_storm.py full > slow_storm_results/full_run.log 2>&1
```

- [ ] **Step 2: Inspect the figures** (`fig_a_slow_bounds.png`, `fig_b_lambda_sensitivity.png`, `fig_c_budget.png`) by reading the PNGs. Check for label collisions and clipped legends before reporting.

- [ ] **Step 3: Write `slow_storm_results/full/SUMMARY.md` by hand.** Include:
  - the headline table (GW), with L\*_SO, L\*_slow, L_slow(x_SO), Δ_mis (GW and %), Δ_rev, L_slow(x_RO) and L\*_RO;
  - the Jaccard index and the added/dropped substations, and whether the added ones flood mainly in speed-05 scenarios;
  - how the near-optimal budget I\* changes across the VOLL × T grid;
  - the regret in $ of keeping the uniform-optimal budget;
  - a numerical confirmation of the robust bound;
  - the scope note that intensity cannot be varied, because all 16 scenarios are Category 5;
  - draft rebuttal sentences.

  Report honestly: if Δ_mis is small, say that the uniform plan is robust to this shift.

- [ ] **Step 4: Ask the user whether to commit.** Results stay untracked; only the code and the spec/plan are committed.

---

## Self-Review Notes

- **Spec coverage.**
  - Metrics A1–A5 come from `build_summary` and `lambda_curves`.
  - B6–B8 come from `_decisions` and `substation_changes`.
  - C9 comes from `budget_table` and `_plot_fig_c`.
  - All four validation groups are in `validation_checks`.
  - Deliverables 1–8 are covered by Tasks 4–8. Deliverable 1 is split into `fixed_plan_vectors.csv` (shared) and `slow_plan_vectors.csv` (per mode).
- **Open questions.** All three spec open questions are implemented with their proposed defaults: a 6 h limit, argmin over the budget grid, and λ = 1 as the only re-optimized weighting. Changing Q1 means passing `time_limit_override=7200` in `run()`. The exact-MILP option in Q2 would be a new task.
- **Δ_rev reference.** Δ_rev and the risk shift use L0_xSO, the evaluated uniform plan, rather than the baseline's 0.5%-gap incumbent. Both sides then come from 1e-4-gap evaluations. The spec wrote L*_SO; the two agree within the baseline gap, which is itself a validation check.
