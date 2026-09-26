# Experiment Specification: The Cost of Being Certain About One Scenario

## Purpose

The manuscript's stochastic model (SO) puts a uniform distribution over the 16 NOAA MEOW scenarios. In effect it says "I have no information about which storm will occur." This experiment looks at the opposite extreme. The planner is fully certain about one scenario k: they put all probability mass on k, solve SO, and implement the resulting hardening plan x_k. We then ask how that plan performs when the truth is still the uniform distribution over all 16 scenarios.

The question it answers: **what is the expected load shed of being (possibly wrongly) certain, compared with hedging across all scenarios?**

## How this differs from wait-and-see, and what it shares with it

This experiment is **not** the wait-and-see bound. The two differ in how a plan is evaluated:

- **Wait-and-see (L*_WS):** the planner *knows* scenario k will happen and hardens for it. The plan x_k is scored only on scenario k, and the result is averaged over k. This is a perfect-information bound: every plan is scored only in the world it was built for.
- **This experiment:** the planner *believes* scenario k will happen and commits to x_k. The truth is still the uniform distribution over all 16 scenarios, so x_k is scored on every scenario: L_SO(x_k). This is the same kind of quantity as L_SO(x̄) for the mean-value plan. A plan built on one assumed scenario is tested on the true distribution. The only difference is that the assumed scenario is one actual MEOW scenario rather than the mean scenario.

What the two share is the **decision step**. Believing k is certain and knowing k is certain lead to the same optimization problem. When all probability sits on scenario k, the other 15 scenarios drop out of the objective, so "SO with a degenerate distribution on k" is the single-scenario model that `output_analysis/Bounds.ipynb` already solves for each (budget, scenario) pair. It is also the same model as EV, with scenario k's column in place of the mean column. Only the evaluation differs.

Consequences for the implementation:

1. No change to `main_model.py` is needed. `two_stage_model` always weights scenarios uniformly by `1/n_scenarios`. We pass it an `input1` that contains only one flood column, `max_flood_level_<k>`, so `n_scenarios = 1`. This is exactly how `Bounds.ipynb` builds the wait-and-see models. We do **not** implement a probability vector with zeros, because it would carry 15 dead scenario blocks and give the same x up to ties.
2. Because the decision step is the same model, the in-sample objective L_k^in of each solve must equal the cached `output_analysis/wait_and_see_dict.json[I][k]`, up to the MIP gap. This is used **only as a correctness check** that the single-scenario model was built correctly. The quantity this experiment reports is L_SO(x_k), not the wait-and-see value.
3. The cache stores only objective values, not the decisions x_k. The 16 × 9 single-scenario solves therefore have to be rerun to recover x_k.

## Notation

Uses the manuscript's notation (Eqs. (5)–(13)) plus these new quantities:

- K is the 16 MEOW scenarios in `fixed_reduced_grid/16_Scenario/`. The uniform probability is p_k' = 1/16.
- x_k(I) is the optimal first-stage decision (x and y for every substation) of the single-scenario model on scenario k at budget I.
- L_k^in(I) is the in-sample objective of that solve, meaning the load shed the certain planner expects. It equals WS_k(I).
- L(x, k') is the load shed in scenario k' under a fixed decision x, computed as Σ_j (D_j − s[j,k']).
- L_SO(x_k) = (1/16) Σ_k' L(x_k, k') is the true expected load shed of the certain plan (out of sample).
- **Regret of certainty:** R_k(I) = L_SO(x_k) − L*_SO(I). This must be ≥ 0 up to the MIP gap.
- **Overconfidence gap:** L_SO(x_k) − L_k^in, the load shed the certain planner fails to anticipate.

The following ordering must hold at every budget, up to the MIP gap. It serves as a validation check:

L*_WS = mean_k L_k^in ≤ L*_SO ≤ min_k L_SO(x_k) ≤ mean_k L_SO(x_k)

L_SO(x̄), the mean-value plan, is reported alongside for comparison. There is no required ordering between L_SO(x̄) and the L_SO(x_k).

## Instructions for Claude

- Reuse `Revision_work/vsc/` wherever you can:
  - `paths.py` for repo-relative paths;
  - `env_check.py`;
  - `baseline.load_config` / `reproduce_baseline` for L*_SO, L_SO(x̄) and L*_WS;
  - the fix-and-resolve loop in `evaluate_decorrelated.py`;
  - `decisions.py` for the Jaccard index, height differences and budget allocation.
- If a VSC helper needs a small generalization, make that change there. Do not copy it.
- Hold every non-flood `model_params` entry at its `config.yaml` value: `fixed_cost`, `variable_cost`, `mit_coarse`, `flexible_generation: True`, `robust_flag: False`, `set_objective: 'min'`, `reference_bus`, `mip_gap`, `solver_method`. For `time_limit`, see open question 2.
- Do not edit checked-in notebooks, `main_model.py`, or `config.yaml`.
- Ask before running anything expensive.

## Step 1: Baseline

For budgets I ∈ {0, 10, …, 80} $M, take L*_SO, x_SO, max_k L(x_SO, k), L_SO(x̄) and L*_WS from `vsc.baseline.reproduce_baseline`.

The VSC pilot only cached the baseline for {20, 40, 60}. If the full 9-budget baseline has not been written yet, compute it once and save it to `certainty_results/baseline.csv`. The VSC full run should be able to reuse the same file.

## Step 2: Solve the certain-planner model (16 scenarios × 9 budgets)

For each scenario column k:

1. Build `input1_k` by dropping all `max_*` columns and adding back only column k. Instantiate one `two_stage_model` and reuse it across budgets by mutating `budget_ref.rhs`, the same pattern as `solve_decorrelated.py`.
2. For each budget I, optimize. Record:
   - x_k and y_k for every substation;
   - L_k^in;
   - the budget actually spent, fc·Σy + vc·Σx;
   - the number of substations hardened;
   - solve time, final gap and status.
3. **Tie-breaking** (open question 1). A single-scenario model has many optimal x:
   - substations that are dry in scenario k have no value in that scenario;
   - at high budgets, scenario k may be fully protected with money left over.

   Gurobi's default choice among ties is arbitrary, and it directly changes L_SO(x_k). The proposed default is a **lexicographic minimum-spend tie-break**:
   1. Solve for L_k^in.
   2. Add the constraint objective ≤ L_k^in + ε, with ε = 1e-6 × max(1, |L_k^in|). The tie-break never accepts more load shed than the phase-1 plan. A tolerance as wide as the MIP gap would let it trade load shed for spend, which is not a tie-break.
   3. Re-optimize minimizing fc·Σy + vc·Σx.

   This models a planner who is certain and does not spend money on scenarios they believe cannot happen. Record the unmodified phase-1 decision as well so the effect of the tie-break can be reported.
4. Validation: |L_k^in − wait_and_see_dict[I][k]| ≤ mip_gap × max(|·|, 1e-6), with an absolute floor. Flag any violations.
5. Save one CSV row after every solve so the run can resume after an interruption. Write `.sol` files to `certainty_results/solves/<k>_<I>M_solution.sol`.

## Step 3: Evaluate each certain plan on all 16 true scenarios

For each (k, I), use the full 16-scenario baseline model and fix `x[i] = round(x_k[i])` for every substation. `y` is implied by the box constraint, and the budget is satisfied because x_k was feasible. Then re-optimize, the same way as `evaluate_decorrelated.evaluate_all`. From that one solve, record:

- L_SO(x_k), the objective;
- the full row L(x_k, k') for all 16 k', read from `s`. This gives a **16 × 16 cross-performance matrix per budget** at no extra cost. Its diagonal should match L_k^in up to the gap, which is another check.
- the worst case, max_k' L(x_k, k').

Record solve time, gap and status.

## Step 4: Metrics

For each (k, I):

- R_k(I);
- the overconfidence gap, in GW and as a % of L_SO(x_k);
- the worst-case gap versus SO: max_k' L(x_k, k') − max_k' L(x_SO, k');
- the comparison versus the mean-value plan: L_SO(x_k) − L_SO(x̄).
- A regret flag: R_k < −mip_gap × L*_SO.

For each budget, across the 16 k: mean, min and max of L_SO(x_k) and R_k, and the identity of the best and worst "certainty" scenario.

**Headline comparison, per budget (the final-stage result):**

avg-certain(I) = (1/16) Σ_k L_SO(x_k(I)) = (1/16) Σ_k (1/16) Σ_k' L(x_k(I), k')

This is an average of averages: each certain plan's average load shed over the 16 true scenarios, averaged over which scenario the planner was certain about. It is compared with planning under uncertainty through the **cost of certainty**, avg-certain(I) − L*_SO(I), in GW and as a % of L*_SO. It appears in `summary.csv` as `L_SO_xk_mean`, `cost_of_certainty` and `cost_of_certainty_pct`.

The **mean over k of L_SO(x_k)** has a direct interpretation. It is the expected load shed of a planner who is certain about one scenario, when the scenario they are certain about is itself a uniformly random draw. This is the headline "expected performance of being certain."

Units: GW = raw objective ÷ 10, following the existing convention in `Bounds.ipynb` and the VSC summary.

## Step 5: Decision comparison

For budgets {20, 40, 60}, compare x_k against x_SO using `vsc/decisions.py`:

- the Jaccard index of the selected substations;
- the number of substations hardened;
- the mean hardening height;
- the mean absolute height difference;
- the fraction of budget spent.

Also report how often each substation is selected across the 16 certain plans, and compare that with SO's selection. This shows which substations every scenario agrees on ("no-regret") and which SO protects only because it hedges.

## Deliverables (in `certainty_results/`)

1. `raw_results.csv`: one row per (k, I) with every quantity from Steps 2–4, including both the tie-broken and the raw phase-1 L_SO(x_k).
2. `cross_matrix_<I>M.csv`: the 16 × 16 matrix L(x_k, k'), one file per budget.
3. `summary.csv` plus a booktabs LaTeX table, one row per budget, with these columns:
   - L*_WS, L*_SO, L_SO(x̄);
   - mean L_SO(x_k) with its [min, max] range;
   - mean regret;
   - the best and worst k.
4. A figure in the style of Figure 5 (colors and markers from `Bounds.ipynb`) showing:
   - the mean-value, stochastic and wait-and-see curves;
   - a new "certain planner" curve: the mean over k, with a shaded min–max band.

   Save it as PDF and PNG.
5. Heatmaps of the cross matrix at $20M, $40M and $60M, with rows = the scenario planned for and columns = the scenario that occurs. Group scenarios by storm direction (w, wnw, nw, nnw) and then by forward speed.
6. A LaTeX table comparing decisions at $20M, $40M and $60M.
7. `validation_report.md` covering:
   - the WS-cache match;
   - the cross-matrix diagonal match;
   - the ordering chain above;
   - regret flags;
   - how often the tie-break changed L_SO(x_k).
8. `SUMMARY.md` with the headline numbers and a short, honest interpretation. Report the result as it comes out. If some single scenario's plan comes close to SO, say so, and say that scenario is only identifiable in hindsight.

## Implementation notes

The implementation lives in `Revision_work/certainty/`, and results go to `certainty_results/{pilot,full}/`. It differs from the layout below in these ways:

- **File names.** Modules are named `certainty_metrics.py`, `certainty_report.py`, `certainty_baseline.py` and `run_certainty.py`. This avoids clashing with `vsc/metrics.py` and `vsc/run_pilot.py`, because both directories are on `sys.path`.
- **L*_SO source.** L*_SO is read from the original Gurobi logs in `output/sm_16/`, together with each solve's final gap, not from the 2-decimal `stochastic_solution.csv`. The baseline at $10M and $20M stopped at the 6 h limit, with gaps of 1.77% and 4.71%. The regret flag and the L*_SO ≤ min_k L_SO(x_k) check therefore allow for the baseline's own gap. A certain plan that beats L*_SO at those budgets is legitimate and gets reported.
- **Open questions resolved with the proposed defaults:**
  - minimum-spend tie-break as the primary result, with the raw plan also evaluated;
  - `config.yaml`'s 6 h time limit;
  - budget $0 included;
  - no robust-model comparison.

## Code layout

`Revision_work/certainty/`:

- `solve_single.py`: Step 2, resumable.
- `evaluate_certain.py`: Step 3, also writes the cross matrices.
- `metrics.py`: Step 4.
- `report.py`: tables, figures and the summary.
- `run_pilot.py` and `run_full.py`: orchestrators.
- `tests/`: pytest tests for the pure-pandas pieces: metrics, the ordering-chain check, and assembling the cross matrix from `s` values. Gurobi-dependent code is validated through the pilot and the WS-cache check.

Imports from `Revision_work/vsc/` go through a sys.path insert, the same way `vsc` imports the repo root.

## Computational notes

- Total work: 144 single-scenario MILPs, plus up to 144 min-spend re-solves, plus 144 fix-and-resolve evaluations on the 16-scenario model. Single-scenario models are about 1/16 the size of SO. These solves already completed for `wait_and_see_dict.json`, so they are expected to be cheap. Fixing x makes the 16-scenario evaluation much easier than a fresh SO solve.
- `config.yaml` does not set `Threads`, so every solve uses all cores. Run solves sequentially unless we explicitly agree on a per-model `Threads` value.
- **Pilot first:** 4 scenarios (one per storm direction, forward speed 10) × budgets {20, 40, 60}. Report solve times for Steps 2 and 3, the WS-cache match, and how much the tie-break matters. Then decide on the full run.

## Open questions for review

1. **Tie-breaking.** Should the primary result use the lexicographic minimum-spend tie-break (proposed), or Gurobi's default solution, which matches how the WS cache was produced? Either way, both are recorded.
2. **Time limit.** Should we use `config.yaml`'s 6 h (proposed, since single-scenario solves should be fast) or reuse the VSC pipeline's 2 h cap?
3. **Budget $0.** It is trivial, since every plan is "harden nothing" and every value equals L*_SO. Should it be included for completeness in the curves (proposed), or skipped?
4. **Scope.** Is the cross matrix plus the uniform-truth evaluation enough? Or do you also want a robust-model comparison, i.e. the worst-case max_k' L against the RO decisions in `output/rm_16/`?
