# The Cost of Being Certain About One Scenario: Full Results

Spec: `Revision_work/single_scenario_certainty_experiment.md`. Code: `Revision_work/certainty/`.
Run: 16 MEOW scenarios × 9 budgets ($0–80M), `mip_gap` 0.5%, 6 h time limit (no solve came close to it). Total run time was about 15 minutes.

## What was done

For each scenario k and budget I, the planner puts all probability on k and solves the stochastic model. This is the single-scenario model. Among plans with equal load shed, the one that spends the least is kept. Each resulting plan x_k is then fixed and evaluated on all 16 scenarios, with every scenario equally likely, which gives L_SO(x_k).

The headline, per budget, is the **average of averages**, (1/16) Σ_k L_SO(x_k). It is compared with the stochastic solution L*_SO.

## Headline (GW)

| Budget | L*_WS | L*_SO | L_SO(x̄) mean-value | **Avg. certain** [best, worst k] | **Cost of certainty** (avg. certain − L*_SO) |
|---|---|---|---|---|---|
| $0M  | 4.462 | 4.462 | 4.462 | 4.462 [4.462, 4.462] | 0.000 |
| $10M | 1.363 | 2.220 | 3.121 | 3.089 [2.590, 3.738] | **0.869** |
| $20M | 0.636 | 1.374 | 2.640 | 2.650 [1.715, 3.660] | **1.276** |
| $30M | 0.277 | 0.830 | 2.352 | 2.415 [1.265, 3.595] | **1.585** |
| $40M | 0.094 | 0.480 | 2.200 | 2.259 [0.965, 3.587] | **1.780** |
| $50M | 0.019 | 0.235 | 2.118 | 2.188 [0.728, 3.587] | **1.953** |
| $60M | 0.001 | 0.060 | 2.115 | 2.169 [0.643, 3.587] | **2.109** |
| $70M | 0.000 | 0.002 | 2.115 | 2.168 [0.633, 3.587] | **2.166** |
| $80M | 0.000 | 0.000 | 2.115 | 2.168 [0.633, 3.587] | **2.168** |

Best k is wnw_5_10 at every budget from $10M upward; worst k is w_5_15. Figure: `certainty_bounds.pdf`. Table: `summary_table.tex`.

## Findings

1. **Being certain is expensive, and the cost grows with budget.** On average, a planner who is certain about one scenario sheds 0.87 GW more than the stochastic plan at $10M. The gap reaches 2.1 GW at $60M. The stochastic plan drives load shed to about zero by $70M. The average certain plan levels off at about 2.17 GW from $50M on, because each certain planner stops investing once its own scenario is protected. Average spend levels off at $46.7M, even when $80M is available.
2. **The average certain plan performs about the same as the mean-value plan.** It is slightly better at $10M (3.09 vs 3.12 GW) and slightly worse from $20M upward (e.g. 2.17 vs 2.12 GW at $60M). Committing to one real storm scenario is, on average, no better than planning for the average flood. Both miss almost all of the value of the stochastic solution.
3. **Even the luckiest choice of scenario is far from the stochastic plan.** The best single-scenario plan (wnw_5_10) reaches 0.63–0.64 GW at $60M+, against 0.06 GW or less for the stochastic plan. No single scenario's plan comes close to what hedging achieves. Which scenario is best is also only knowable in hindsight.
4. **Certain planners badly misjudge their own risk.** The planner expects L_k^in (their wait-and-see value), which is about 0 from $50M up. On average they actually get 2.17 GW. At $40M the average worst-case scenario is 4.48 GW for a certain plan, versus 0.75 GW for the stochastic plan.
5. **The certain plans harden different substations from the stochastic plan.** At $20M, $40M and $60M, the Jaccard overlap of hardened substations between a certain plan and the stochastic plan averages 0.51, 0.58 and 0.63. At $60M, the stochastic plan hardens 58 substations. Only 24 of them are chosen by all 16 certain plans, and 1 is chosen by none. Details: `decision_comparison.tex` and `selection_frequency.csv`.

The heatmaps (`cross_heatmap_{20,40,60}M.pdf`) show the mechanism. Each certain plan has near-zero load shed on its own diagonal cell and 3–5 GW off it. The damage is largest when the plan was built for a w or nnw track and a wnw or nw storm occurs.

## Validation (all passed; see `validation_report.md`)

- 144/144 in-sample solves match `wait_and_see_dict.json` within the MIP gap. This confirms the decision step is the same model as in the wait-and-see computation. The mean over k reproduces L*_WS at every budget.
- 144/144 cross-matrix diagonals match their in-sample value.
- The ordering L*_WS ≤ L*_SO ≤ min_k L_SO(x_k) ≤ mean_k L_SO(x_k) holds at every budget. No certain plan beats L*_SO, including at $10M and $20M, where the baseline had 1.8% and 4.7% gaps.
- **Tie-break sensitivity:** the least-spend choice changed L_SO(x_k) in 56/144 cases. The largest change was 0.04 GW, and the averages changed by at most 0.01 GW, so the conclusions don't depend on it. Gurobi's original plans also level off in spend. The flat curve reflects what a certain planner would do, not an artifact of the tie-break.
- The baseline mean-value numbers at $20M, $40M and $60M match the VSC pilot (2.640, 2.200 and 2.115 GW).
