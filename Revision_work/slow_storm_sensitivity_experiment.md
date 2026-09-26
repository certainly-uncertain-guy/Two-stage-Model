# Experiment Specification: Sensitivity to Scenario Weights When Future Storms Move Slower

## Purpose

This experiment responds to Reviewer 3, comment 1 (`rebuttal.tex`). The reviewer accepts the maximum-entropy argument and the robust model, but asks for a **quantitative** sensitivity analysis under non-uniform scenario weights. Specifically, the reviewer asks how different weights by storm direction, translation (forward) speed and intensity affect three things:

1. the hardening plan;
2. the load loss;
3. the long-term budget.

This experiment tests one physically motivated alternative: **future hurricanes move more slowly**. We move the probability mass of the fast-moving MEOW scenarios onto the slowest-moving ones.

In this data set the fastest storms are the mildest:

| speed label | 05 | 10 | 15 | 25 |
|---|---|---|---|---|
| flooded substations, mean over directions (of 72 in I_f) | 56.5 | 57.5 | 52.3 | 47.0 |
| mean flood height at flooded substations (ft) | 6.7 | 7.4 | 6.5 | 5.7 |

So shifting mass from speed 25 to speed 05 makes the scenario set more severe. The most severe speed, however, is 10, not 05. We then measure:

- how far the uniform-weight hardening plan is from optimal under the shifted weights (load loss);
- how much the re-optimized plan differs from the uniform plan (hardening plan);
- how the near-optimal hardening budget moves (long-term budget).

The results also give a direct numerical check of the rebuttal's current argument. Under any weighting, the expected load shed of the robust plan cannot exceed L*_RO.

**Scope note on intensity.** All 16 retained scenarios are Category 5 (`max_flood_level_<direction>_5_<speed>`), so there is no intensity dimension to reweight within this scenario set. The rebuttal should state this explicitly and not imply that intensity was varied. Direction weights are left uniform in this experiment; see open question 3.

## Scenario set and weightings

The set K contains 16 scenarios: 4 directions {w, wnw, nw, nnw} × 4 forward-speed labels {05, 10, 15, 25}. Under the manuscript's uniform weights, p_k = 1/16.

**Slow-storm shift with parameter λ ∈ [0, 1].** Within every direction, a fraction λ of the fastest scenario's mass (speed 25) moves to the slowest scenario (speed 05):

| speed | 05 | 10 | 15 | 25 |
|---|---|---|---|---|
| p_k (per direction) | (1+λ)/16 | 1/16 | 1/16 | (1−λ)/16 |

- λ = 0 is the manuscript's uniform distribution.
- **λ = 1 is the primary "slow future" case, p^slow:** speed-05 scenarios get 2/16, speed-25 scenarios get 0, and speeds 10 and 15 stay at 1/16.
- Direction marginals stay at 1/4 each, so only the speed distribution changes.
- The expected forward-speed label drops from 13.75 to 8.75.

Evaluating a fixed plan under this weighting costs nothing extra (see below). Plans are therefore evaluated over the whole grid λ ∈ {0, 0.25, 0.5, 0.75, 1}. The plan is re-optimized only at λ = 1.

## Key observation: what is cheap and what is not

For a fixed first-stage decision x, the second stage separates by scenario. The load shed L(x, k) in scenario k does not depend on the weights. So for any weighting p:

L_p(x) = Σ_k p_k L(x, k).

Once we have the 16-vector (L(x, 1), …, L(x, 16)) for a plan, its expected load shed under **any** weighting is a dot product. This covers the uniform SO plan x_SO, the robust plan x_RO and the mean-value plan x̄. No new optimization is needed for those beyond one fix-and-resolve per plan and budget.

The only expensive part is **re-optimizing** the plan under p^slow: x_slow(I) = argmin_x L_{p^slow}(x) subject to the budget. This is a new SO solve per budget, of the same kind as `output/sm_16/`, which took up to 6 h per budget.

## Notation

- L*_SO(I), x_SO(I): the manuscript's uniform SO optimum and plan. Plans are read from `output/sm_16/<I>M_solution.sol`.
- x_RO(I): the robust plan from `output/rm_16/<I>M_solution.sol`. L*_RO(I) comes from `output/rm_16/robust_solution.csv`, or from the logs for full precision.
- x̄(I): the mean-value plan (rounded EV solution), as in `vsc.baseline._mean_value_bound`.
- L(x, k): per-scenario load shed of plan x, as above.
- L_λ(x) = Σ_k p^λ_k L(x, k), with L_0 = uniform and L_1 = L_slow.
- L*_slow(I), x_slow(I): optimum and plan of SO re-solved with weights p^slow.
- WS_slow(I) = Σ_k p^slow_k WS_k(I), the wait-and-see bound under p^slow, taken from `wait_and_see_dict.json`.

## Metrics (per budget I)

**A. Load loss: does the uniform assumption cost anything if storms are slower?**

1. **Misspecification cost:** Δ_mis(I) = L_slow(x_SO) − L*_slow ≥ 0. This is the extra expected load shed from keeping the uniform plan when the truth is p^slow. Report it in GW and as a % of L*_slow.
2. **Reverse cost:** Δ_rev(I) = L_0(x_slow) − L*_SO ≥ 0. This is the extra load shed from planning for slow storms when the truth is uniform.
3. **Shift in the level of risk:** L*_slow vs L*_SO, i.e. how much the optimal expected load shed itself changes when storms are slower.
4. **Robust bound check:** L_λ(x_RO) ≤ L*_RO for every λ, up to the MIP gap. This is the rebuttal's claim, verified numerically.
5. **Fixed-plan sensitivity curves:** L_λ(x_SO), L_λ(x_RO) and L_λ(x̄) for λ ∈ {0, 0.25, 0.5, 0.75, 1}.

**B. Hardening plan:**

6. The Jaccard index of hardened-substation sets for x_slow vs x_SO.
7. The number of substations hardened, the mean hardening height, the mean absolute height difference on substations both plans harden, and the budget used.
8. The substations added and dropped by x_slow relative to x_SO, with their flood heights in the speed-05 vs speed-25 scenarios. This tests whether re-weighting moves investment toward substations that flood mainly in slow storms.

**C. Long-term budget:**

9. The near-optimal budget under each weighting, using the manuscript's disaster-cost model:

   TotalCost(I) = I + γ · T · VOLL · 100 · L(I),

   with γ = 10 storms (the `Optimal_budget.ipynb` default), T ∈ {6, 12, 24, 48} h, VOLL ∈ {250, 500, 1000, 3000, 5000} $/MWh, and L in raw units (per-unit × 100 MW). Compute:
   - I*_SO = argmin over the 9-budget grid, using L*_SO(I);
   - I*_slow = argmin using L*_slow(I);
   - the total cost of adopting I*_SO's plan when the truth is slow, versus the slow optimum.

   See open question 2 for the exact (unconstrained-MILP) variant.

## Validation checks

- **Uniform reproduction.** The uniform average of x_SO's per-scenario vector reproduces the log value of L*_SO within the MIP gap. The uniform average of x_RO's vector reproduces `robust_decisions_stochastic_solutions.csv`, and its max reproduces L*_RO. The uniform average of x̄'s vector reproduces L_SO(x̄) from `certainty_results/baseline.csv`.
- **Optimality ordering under p^slow:** WS_slow ≤ L*_slow ≤ L_slow(x_SO), and L*_slow ≤ L_slow(x̄). The tolerance is the re-solve's final gap.
- **Robust bound:** L_λ(x_RO) ≤ L*_RO for every λ.
- **Consistency:** L*_slow reported by the solver equals Σ_k p^slow_k L(x_slow, k) from x_slow's own fix-and-resolve.

## Instructions for Claude

- **Weighted objective without editing `main_model.py`.** Build `two_stage_model` on an `input1` that keeps only the scenarios with p_k > 0: 12 of the 16 columns at λ = 1. Then replace the objective with `load.sum() − Σ_k p_k Σ_i s[i,k]`. Use the same explicit expression for any later constraint or post-check. `getObjective()` drops the constant; this bug was already hit once in the certainty experiment.
- **Per-scenario vectors.** Fix x (y is implied) on the full 16-scenario model and re-optimize, as in `certainty/evaluate_certain.py`. Read L(x, k) from `s`. Because these vectors are reweighted, run these evaluation solves with **MIPGap = 1e-4** rather than 0.5%. That keeps each scenario's entry accurate, not just their sum. The solves take seconds.
- **Warm start** each x_slow(I) solve from x_SO(I) (set `.Start` on x and y), and sweep budgets in ascending order.
- **Solver settings.** Hold every other `config.yaml` entry fixed. For the time limit, see open question 1.
- **Reuse existing helpers:**
  - `vsc/paths.py` and `vsc/env_check.py`;
  - `vsc/baseline.load_config(time_limit_override=…)`;
  - `certainty/common.py` (append-row resumability, solver params);
  - `certainty_results/baseline.csv` (x_SO, L_SO(x̄), exact L*_SO and gaps);
  - `vsc/decisions.py` (Jaccard, heights).
- **Do not edit** `main_model.py`, `config.yaml`, or any checked-in notebook.
- **Ask before running anything expensive.** Run a pilot first.

## Deliverables (`slow_storm_results/`)

1. `per_scenario_vectors.csv`: one row per (plan ∈ {SO, RO, MV, SLOW}, budget), with L(x, k) for all 16 k, plus solve time and gap.
2. `slow_solves.csv`: L*_slow, x_slow, and the solve time, gap and status per budget. Resumable.
3. `summary.csv` plus a booktabs LaTeX table, one row per budget, with these columns:
   - L*_SO and L*_slow;
   - L_slow(x_SO) and Δ_mis (GW and %);
   - L_0(x_slow) and Δ_rev;
   - L_slow(x_RO) and L*_RO;
   - WS_slow;
   - the Jaccard index of x_slow vs x_SO.
4. **Figure A** (Figure 5 style): expected load shed vs budget under p^slow, with the curves
   - L*_slow (re-optimized);
   - L_slow(x_SO) (uniform plan);
   - L_slow(x_RO) (robust plan), with the L*_RO line dashed;
   - L_slow(x̄);
   - WS_slow.
5. **Figure B**: sensitivity to λ at budgets $20M, $40M and $60M, as small multiples. Each panel shows L_λ(x_SO) and L_λ(x_RO) for λ ∈ [0, 1], plus the L*_RO line and the re-optimized L*_slow point at λ = 1.
6. **Figure C**: the near-optimal budget I* under uniform vs slow weights across VOLL, one panel per restoration time T.
7. `decision_comparison.tex` and `substation_changes.csv`, for metrics 6–8.
8. `validation_report.md` and `SUMMARY.md`. The latter holds the headline numbers and draft rebuttal sentences, reported honestly: if the uniform plan turns out to be nearly optimal under slow storms, say that plainly.

## Computational notes

- Cost: 8 nontrivial x_slow solves ($0M is trivial), each an SO MILP over 12 scenarios. The uniform 16-scenario baseline took 0.3–6 h per budget, and $10M and $20M hit the 6 h cap. The 12-scenario model with a warm start should be faster, but budget up to about 30 h wall-clock for the full sweep at a 6 h cap.
- All evaluations: (3 fixed plans + x_slow) × 9 budgets = 36 fix-and-resolve solves of a few seconds each.
- Solve sequentially: `config.yaml` sets no `Threads`.
- **Pilot:** re-optimize x_slow at $20M, $40M and $60M only, and compute everything else at all budgets, since it is cheap. Report timings, then decide on the full sweep.

## Open questions for review

1. **Time limit for the x_slow re-solves.** The proposal is 6 h, matching the manuscript's L*_SO runs, so L*_slow and L*_SO are comparable. The alternative is the VSC pipeline's 2 h cap, which is faster but may leave larger gaps at $10M–30M.
2. **Long-term budget method.** The proposal is argmin over the 9-point budget grid, which is cheap but only resolves the budget to within $10M. The alternative is re-running `Optimal_budget.ipynb`'s unconstrained MILP (min hardening cost + γ·T·VOLL·100·L) with p^slow weights for each (T, VOLL) pair. That gives exact budgets, but it is up to 20 more hard MILPs.
3. **Scope of the shift.** The primary case moves speed-25 mass onto speed 05 (λ = 1). Should we also re-optimize a stronger shift that moves both the 15 and 25 mass onto 05? That gives, per direction, 3/16 on speed 05, 1/16 on speed 10, and 0 on speeds 15 and 25. Or a direction-weighted case? Each additional re-optimized weighting costs another about 8 SO solves.
