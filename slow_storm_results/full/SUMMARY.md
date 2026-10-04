# Slow-Storm Scenario-Weight Sensitivity: Results

Spec: `Revision_work/slow_storm_sensitivity_experiment.md`. Code: `Revision_work/slow_storm/`. Responds to Reviewer 3, comment 1.

## What was done

Within each storm direction, a fraction λ of the fastest scenario's probability (speed 25) was moved to the slowest (speed 05). At λ = 1:

- speed-05 scenarios get 2/16 each;
- speed-10 and speed-15 scenarios keep 1/16 each;
- speed-25 scenarios get 0.

Direction weights stay at 1/4 each. In this data set, speed-25 storms are the mildest, so the shift makes the scenario set more severe.

For every budget ($0–80M), we then:

1. **Re-optimized the stochastic model under the slow weights**, giving x_slow. The solves were warm-started from the uniform plan and used the manuscript's settings: 0.5% MIP gap and a 6 h limit. Every solve finished in under 65 min. All 9 finished with optimal status within the 0.5% gap. Four ($50M–$80M) closed the gap completely, and $10M closed it to 6e-6.
2. **Scored four fixed plans (uniform SO, robust, mean-value and x_slow) under any weighting.** Each plan was evaluated per scenario on all 16 MEOW scenarios at a 1e-4 gap, and each weighting then became a reweighted average.
3. **Computed the near-optimal budget under both weightings**, using the manuscript's cost model: γ = 10 storms, T ∈ {6, 12, 24, 48} h and VOLL ∈ {250, …, 5000} $/MWh.

Units are GW (raw objective ÷ 10) unless stated otherwise.

## 1. Load loss

| Budget | L*_SO (uniform) | Uniform plan under slow weights | Re-optimized under slow weights, L*_slow | **Cost of keeping the uniform plan** | Robust plan under slow weights / L*_RO |
|---|---|---|---|---|---|
| $0   | 4.462 | 4.645 | 4.645 | 0.000 | 4.645 / 5.604 |
| $10M | 2.220 | 2.263 | 2.261 | **0.002 (0.1%)** | 2.406 / 2.581 |
| $20M | 1.374 | 1.419 | 1.385 | **0.034 (2.4%)** | 1.516 / 1.571 |
| $30M | 0.830 | 0.848 | 0.839 | **0.009 (1.1%)** | 0.900 / 0.992 |
| $40M | 0.480 | 0.499 | 0.479 | **0.020 (4.2%)** | 0.502 / 0.526 |
| $50M | 0.235 | 0.249 | 0.233 | **0.015 (6.5%)** | 0.250 / 0.254 |
| $60M | 0.060 | 0.061 | 0.057 | **0.004 (6.4%)** | 0.061 / 0.062 |
| $70M | 0.002 | 0.002 | 0.002 | 0.000 | 0.002 / 0.002 |
| $80M | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 / 0.000 |

- **The uniform plan is nearly optimal under slow storms.** Keeping it costs at most 0.034 GW of extra expected load shed, at $20M. At $50M–$60M the relative figures of about 6.5% sit on bases of only 0.06–0.25 GW.
- **The overall risk level barely moves.** Slow storms raise the unhardened expected load shed from 4.46 to 4.65 GW (+4%). With hardening, the optimal expected load shed under slow weights is within 0.041 GW of L*_SO at every budget from $10M upward, and within 0.011 GW from $20M upward.
- **Over the whole λ ∈ [0, 1] range,** the uniform plan's expected load shed grows linearly. From $10M upward it rises by at most 0.045 GW (`fig_b_lambda_sensitivity`); at $0, with no hardening, it rises by 0.18 GW.
- **The robust bound holds numerically.** Under every λ and at every budget, the robust plan's expected load shed stays below L*_RO, as the rebuttal argues.
- **The reverse mistake is also small.** Planning for slow storms when the truth is uniform costs at most 0.018 GW.

## 2. Hardening plan

| Budget | Substations hardened (uniform / slow) | Mean height, ft (uniform / slow) | Jaccard overlap |
|---|---|---|---|
| $10M | 13 / 13 | 7.38 / 7.38 | 1.00 |
| $20M | 27 / 26 | 7.15 / 7.42 | 0.89 |
| $30M | 36 / 35 | 8.08 / 8.31 | 0.97 |
| $40M | 44 / 44 | 8.84 / 8.84 | 0.96 |
| $50M | 52 / 52 | 9.37 / 9.37 | 0.93 |
| $60M | 58 / 58 | 10.09 / 10.09 | 0.97 |
| $70M | 65 / 65 | 10.51 / 10.51 | 0.97 |
| $80M | 72 / 71 | 9.92 / 9.97 | 0.99 |

The re-optimized plans harden nearly the same substations: the overlap is 0.89–1.00, and the number hardened is the same to within one. At each budget, 2–9 substations change (`substation_changes.csv`). Most changes are height adjustments of 1–2 ft, but some are larger:

- 1074: 2 → 6 ft at $50M;
- 327: 2 → 5 ft at $30M;
- 1096, which floods 7.75 ft in speed-05 storms, dropped from 11 ft at $50M;
- 1084 (5 ft) added at $60M;
- 288 (6 ft) added at $70M.

The changes follow the reweighting. The slow plan raises walls where slow storms flood deeper, for example:

- 311: 3.25 ft mean flood at speed 05 vs 0.25 ft at speed 25;
- 327: 3.50 vs 1.25 ft;
- 1130: 4.00 vs 0.00 ft.

It lowers walls where fast storms flood deeper:

- 301: 8.75 vs 10.75 ft;
- 297: 6.50 vs 7.75 ft;
- 1075: 5.75 vs 11.50 ft.

Substation 314 floods only in one fast scenario (1 ft in w_5_25). The uniform plan hardens it from $30M upward; the slow plan never does. None of these changes moves expected load shed by more than 0.034 GW (Section 1).

## 3. Long-term budget

The near-optimal budget is the argmin over the $10M budget grid of hardening cost plus γ·T·VOLL·100·L. It is **identical under uniform and slow weights in 19 of 20 (T, VOLL) combinations**. The one exception is T = 6 h, VOLL = $3000/MWh, where it moves from $70M to $60M.

Suppose you keep the uniform-optimal budget and plan when storms are actually slower. The total disaster cost then exceeds the slow-storm optimum by only **$0.1M–$0.9M**, on totals of $40M–$75M (`budget_table.csv`, `fig_c_budget`).

## Validation

116 of 117 pass/fail checks pass (`validation_report.md`):

- The uniform average of each fixed plan reproduces L*_SO and L_SO(x̄).
- The robust plan's worst-case scenario never exceeds the `output/rm_16` logs' L*_RO, and matches it to within 0.2%.
- WS_slow ≤ L*_slow ≤ L_slow(x_SO) and ≤ L_slow(x̄) at every budget, within the MIP gap. At $0, WS_slow exceeds L*_slow by 0.005%, because the cached wait-and-see values come from 0.5%-gap solves.
- Each solver objective equals the re-evaluated value.

The one failure is in an existing file, not this pipeline. `output/rm_16/robust_decisions_stochastic_solutions.csv` reports 8.70 at $30M. The robust plan in `30M_solution.sol`, which reproduces that budget's robust log, evaluates to 8.77. That CSV entry most likely came from an earlier robust run.

**A finding about the manuscript's baseline.** At $20M the slow-weight re-solve found a plan that is also better under **uniform** weights: 1.366 vs 1.374 GW. That is consistent with the original $20M SO run stopping at its 6 h limit with a 4.7% gap. The validation report now flags this automatically as an informational item (negative Δ_rev). The manuscript's L*_SO at $20M is therefore at least 0.6% above the true optimum. This does not change any conclusion.

## Scope

- **Intensity is not varied.** All 16 retained scenarios are Category 5, so intensity cannot be reweighted within this scenario set.
- **Direction weights are held uniform.** Only the forward-speed distribution changes.
- **Grid resolution.** The near-optimal budget is resolved only to the $10M grid. Spec open question 2 describes the exact alternative, re-running `Optimal_budget.ipynb`'s MILP with slow weights.

## Draft rebuttal text (starting point)

> To complement the distribution-free argument above with a quantitative sensitivity analysis, we examined a physically motivated alternative weighting in which future hurricanes move more slowly. Within each storm direction, we shifted the probability mass of the fastest-moving MEOW scenarios (forward-speed 25) onto the slowest-moving ones (forward-speed 05), in increments up to a complete shift, and re-solved the stochastic model under the fully shifted weights for every budget. The results show that our recommendations are insensitive to this change. (i) Load loss: retaining the hardening plan obtained under uniform weights increases expected load shed under the shifted weights by at most 0.034 GW relative to the re-optimized plan, across all budgets. (ii) Hardening plan: the re-optimized plans select essentially the same substations (Jaccard overlap 0.89–1.00, with the same number of hardened substations to within one). (iii) Long-term budget: the near-optimal budget is unchanged in 19 of the 20 combinations of restoration time and value of lost load that we consider, and adopting the uniform-weight budget costs at most \$0.9M more over the planning horizon. Consistent with the argument above, the robust plan's expected load shed under every shifted weighting remained below the robust objective $L^*_{\mathcal{RO}}$. We note that all retained scenarios are Category 5, so intensity weights cannot be varied within this scenario set.
