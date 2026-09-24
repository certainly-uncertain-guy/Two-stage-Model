# Experiment Specification: Isolating the Value of Spatial Correlation

## Purpose

A reviewer pointed out that comparing the stochastic model (SO) against the mean-value (EV) model cannot isolate the effect of spatial correlation in the NOAA MEOW flood scenarios, because the mean scenario removes both the marginal variability of flood heights at each substation and their joint dependence across substations. The relevant passage in the manuscript is Section 6.1 (the L*_SO, L_SO(x̄), and VSS discussion around Eq. (10)-(11) and Figure 5), together with the framing added in Section 5.1 that the NOAA MEOW maps are used specifically because they "preserve spatial correlation across substations."

This experiment adds a decorrelated benchmark. The benchmark keeps the marginal flood height distribution of every substation exactly unchanged, but it destroys the dependence across substations. Comparing SO against this benchmark isolates the value of spatial correlation (VSC) and decomposes the value of the stochastic solution into two parts, using the same VSS defined in the manuscript's Eq. (11) (VSS = L_SO(x̄) − L*_SO):

VSS = [ L_SO(x_bar) − L_SO(x_IND) ] + [ L_SO(x_IND) − L*_SO ]

* The first bracket is VMV, the value of representing marginal flood variability.
* The second bracket is VSC, the value of representing spatial correlation.

VSC is a new quantity for the rebuttal; it does not appear in the manuscript. VSS, L*_SO, L_SO(x̄), and L*_WS are the manuscript's own notation (Eqs. (5)-(13)) and must be reproduced exactly, not redefined.

## Instructions for Claude

Before writing any new code, do the following.

1. Inspect the repository and locate the existing implementation of:
   * the two-stage SO model in `main_model.py` (`two_stage_model` class) — first-stage constraints (6a)/(6b) are `budget_constraint`/`box_constraints`, and the recourse (7a)-(7m) is built by `linking_and_capacity_constraints`, `edge_constraints`, `flow_balance_constraints`, and `phase_angle`;
   * the EV model and the evaluation routine that fixes a first-stage decision and computes the expected load shed over all scenarios — this already exists in `output_analysis/Bounds.ipynb`: the mean-value flood column is built as `np.ceil(flood_df.mean(axis=1))`, the EV model is solved as a single-scenario `two_stage_model`, and `L_SO(x̄)` is obtained by adding equality constraints that fix `x[i]` to the rounded EV solution on a full multi-scenario model and re-optimizing;
   * the wait-and-see computation — already cached in `output_analysis/wait_and_see_dict.json` (one single-scenario SO solve per budget × scenario column), aggregated into `L*_WS(I)` in `Bounds.ipynb`; reuse this cache rather than resolving it;
   * the flood height data (the matrix Δ with one row per substation and one column per scenario) — this is the set of columns matching `max_flood_level_*` in `Final_Input1.csv` (`self.filter_col` in `main_model.py`), given per bus row but identical across every bus belonging to the same substation;
   * the grid data — `fixed_reduced_grid/16_Scenario/Final_Input1.csv` / `Final_Input2.csv`, the reduced ACTIVSg2000 network (663 buses, 362 substations per Table 1 of the manuscript).
   * how hardening decisions are read back out of a solved model: `output_analysis/analysis.py` reads a `.sol` file into a rebuilt `two_stage_model` via `model.read(...)` and pulls `x[i]`/`y[i]` (and, in `Discussion.ipynb`'s `load_profile_plotter`, `s[i,j]`) via `model.getVarByName(...).Start`. Reuse this pattern rather than re-deriving decisions by hand.
2. Summarize what you found, including file names, function/class names, the number of scenarios, the size of the set of flooded substations I_f, and the Gurobi settings currently used (MIP gap, time limit, threads). As a cross-check, confirm or correct the following, which were established during scoping and should match unless something has changed: the primary case study uses the 16-scenario set in `fixed_reduced_grid/16_Scenario/` (4 storm directions × category 5 × 4 forward speeds, matching the manuscript's Section 5.1 scenario-reduction description), 362 total substations, 663 buses, and 72 substations in I_f. Note that `config.yaml` never sets Gurobi's `Threads` parameter, so every solve uses all available cores by default — flag this explicitly, since it affects whether replications can safely be run concurrently (see Computational notes).
3. Several notebooks and `output_analysis/analysis.py` hardcode absolute paths from the original author's machine (e.g. `/Users/ashutoshshukla/Desktop/...`, or a sibling `Data/` directory outside this repo). Identify every such path you will need to touch for this experiment and repoint it at this repo's `fixed_reduced_grid/16_Scenario/` and `output/sm_16/` before running anything — do this only in the copies/scripts you write for this experiment, not by editing the checked-in notebooks, unless I ask you to.
4. Ask me to confirm before running anything expensive.

Reuse the existing model code wherever possible. The only new ingredient is a different scenario set passed to the same SO model. Do not reimplement the model unless the existing code cannot accept an arbitrary scenario matrix. If it cannot, make the smallest change that allows it. Whenever you instantiate `two_stage_model` for this experiment, hold every other `config.yaml`-derived entry in `model_params` fixed at its current value (`fixed_cost`, `variable_cost`, `mit_coarse`, `flexible_generation`, `robust_flag: False`, `set_objective: 'min'`, `reference_bus`, `mip_gap`, `time_limit`, `solver_method`) — the only thing that should differ between the baseline SO and any decorrelated run is `input1`'s flood columns.

## Step 1: Reproduce the baseline

Before doing anything new, reproduce the existing numbers so that all comparisons use the same code and solver settings.

For every budget I in {0, 10, 20, 30, 40, 50, 60, 70, 80} million dollars — this is the exact sweep already used for Figure 5, `output/sm_16/`, `output_analysis/analysis.py`'s default `budget_vector`, and the cached `wait_and_see_dict.json` — compute:

1. L*_SO(I): the optimal expected load shed of SO on the original MEOW scenarios, along with the optimal first-stage decision x_SO (y and x values for every substation in I_f). Prefer reloading the existing `.sol` files in `output/sm_16/` via the `analysis.py` pattern over resolving from scratch; only resolve if a `.sol` file is missing or you need a fresh model object to extract additional quantities (see item 4 below).
2. L_SO(x_bar): the expected load shed of the EV solution evaluated on the original MEOW scenarios, following the `Bounds.ipynb` mean-value pipeline described above.
3. L*_WS(I): the wait-and-see bound, aggregated from the cached `wait_and_see_dict.json` exactly as `Bounds.ipynb` does — do not resolve the 9 × 16 wait-and-see MILPs unless the cache is missing or you suspect it is stale.
4. max over k of L(x_SO, k): the worst-case scenario load shed of the SO decision. Do not solve this separately per scenario — extract per-scenario load shed sum_j(D_j − s[j,k]) directly from the already-solved SO model's `s` variables (same technique as `Discussion.ipynb`'s `load_profile_plotter`), since the SO model already contains all 16 scenarios jointly.

Check that these match Figure 5 of the manuscript. At budget 0, all three expected values must coincide. As a secondary, optional sanity check, note that the manuscript separately reports a minimum budget of $71.35M for zero expected load shed across all scenarios, computed via a *different* formulation (no budget constraint, minimize total hardening expenditure, force `s[j,k] = D_j` for all j, k in place of (7f)) — this is not one of the swept budgets and does not need to be reproduced for this experiment; it is only useful to confirm that the sweep's L*_SO curve is at or near zero by budget $80M. If the main sweep values do not match the paper, stop and report the discrepancy.

## Step 2: Construct decorrelated scenario sets

Let K be the set of original scenarios and Δ[i, k] the flood height at substation i in scenario k.

For each replication r = 1, ..., R with R = 20:

1. Set the random seed to r so that the construction is reproducible.
2. For each substation i in I_f, draw an independent random permutation π_i of the scenario indices.
3. Define the decorrelated flood height as Δ_tilde_r[i, k] = Δ[i, π_i(k)].
4. Substations outside I_f are never flooded, so leave their rows as zeros.
5. Keep scenario probabilities uniform, exactly as in the original SO.

Buses inside the same substation continue to share one flood height. This is physically correct and intended. Concretely, `Final_Input1.csv` stores one flood column value per bus row, but every bus belonging to the same `SubNum` already carries the identical value in the original data — when writing Δ_tilde_r back into the per-bus data frame passed to `two_stage_model`, apply the permuted substation-level value to every bus row of that substation, not to bus rows independently. Doing the permutation at the bus-row level instead of the substation level would silently decorrelate buses within a substation and violate the shared-flood-height assumption the model constraints rely on (`linking_and_capacity_constraints` in `main_model.py` looks up one flood value per bus but only ever varies it by substation).

### Validation checks for Step 2

Run these checks for every replication and save the results:

1. **Marginals preserved.** For every substation, the sorted vector of flood heights in the decorrelated set must equal the sorted vector in the original set. Assert this exactly. Compute the vector once per substation (e.g. take any one bus row per `SubNum`, or `groupby("SubNum").first()`), not once per bus row.
2. **Same flooded set.** The set of substations flooded in at least one scenario must be identical to I_f.
3. **Correlation destroyed.** Compute the mean pairwise Spearman correlation of flood heights across substations in I_f (only pairs where both substations have nonconstant flood heights), once for the original matrix and once for each decorrelated matrix. Report both. The original should be clearly positive and the decorrelated one close to zero.
4. **Count of simultaneous failures.** For each scenario, count how many substations are flooded (flood height greater than zero). Report the mean, standard deviation, and maximum of this count for the original and decorrelated sets. This shows how independence changes the pattern of simultaneous failures and will be useful in the paper discussion.
5. **Shared-height invariant.** For every substation and every scenario, confirm that all bus rows belonging to that substation still carry an identical flood value after permutation. This catches an accidental bus-level (rather than substation-level) permutation.

## Step 3: Solve SO on the decorrelated scenarios

For every replication r and every budget I from Step 1:

1. Solve the SO model with the decorrelated scenario set Δ_tilde_r and budget I. Call the optimal first-stage decision x_IND(r, I) and its objective value L_IND_in(r, I). The latter is the expected load shed the decorrelated model believes it will achieve (in-sample estimate).
2. Use exactly the same Gurobi settings and the same non-flood `model_params` entries as the baseline in Step 1 (see the instruction at the end of "Instructions for Claude").
3. Record the solve time, final MIP gap, and solver status.

## Step 4: Evaluate the decorrelated decisions on the true MEOW scenarios

For every replication r and budget I:

1. Take the baseline multi-scenario SO model already built on the original MEOW scenarios (the same one used in Step 1), add equality constraints fixing `x[i]` (and `y[i]`) to x_IND(r, I) for every substation, and re-optimize. This is the same fix-and-resolve pattern `Bounds.ipynb` already uses to compute `L_SO(x_bar)` — it solves a single joint MILP over all 16 original scenarios rather than 16 separate single-scenario solves, and should be considerably cheaper since fixing x/y pins most of the `z` variables via the flood-linking constraints (7b)/(7c).
2. From that one solve, compute:
   * L_SO(x_IND): the objective value of the resolved model (the expected load shed on the original scenarios, out of sample, true performance);
   * max over k of L(x_IND, k): extract per-scenario load shed sum_j(D_j − s[j,k]) from the same solution (as in Step 1, item 4) rather than solving each scenario separately.
3. Only fall back to solving each original scenario independently (fixing x/y, one single-scenario model per k) if the joint fix-and-resolve approach in step 1 above turns out not to be materially faster in practice — check this on the pilot run in the Computational notes before committing to either approach for the full run.

## Step 5: Compute the metrics

For every budget I, compute the following for each replication, then report the mean, minimum, and maximum across the 20 replications:

1. VSC(I) = L_SO(x_IND) − L*_SO. This must be nonnegative up to the MIP gap tolerance. Flag any replication where it is negative beyond the gap.
2. VMV(I) = L_SO(x_bar) − L_SO(x_IND), the value of marginal variability. This can be negative in principle. Report it as observed.
3. VSS(I) = L_SO(x_bar) − L*_SO, and verify that VMV + VSC equals VSS.
4. The share of VSS attributable to correlation, VSC divided by VSS, reported only when VSS is greater than zero.
5. Misestimation by the decorrelated model: L_IND_in − L_SO(x_IND), in GW and as a percentage of L_SO(x_IND). A negative value means that assuming independence underestimates the true load shed.
6. Worst-case gap: max over k of L(x_IND, k) minus max over k of L(x_SO, k).
7. Optionally, also report EVPI(I) = L*_SO(I) − L*_WS(I) (the manuscript's Eq. (13)) alongside these metrics for context — it is already computed in Step 1 and costs nothing extra to include in the summary table.

## Step 6: Compare the hardening decisions

For budgets I in {20, 40, 60} million, compare x_SO against x_IND for every replication. Extract both using the same `.sol`-read-plus-`getVarByName` pattern as `analysis.py`, so the comparison uses decisions read back the same way as the rest of the codebase does:

1. **Selection overlap.** Compute the Jaccard index between the set of substations selected for hardening (y equal to 1) by SO and by IND.
2. **Height differences.** For substations selected by both models, compute the mean absolute difference in hardening height in feet.
3. **Budget allocation.** Report the number of substations hardened and the average hardening height for each model.
4. **Frequency map.** For every substation, compute the fraction of the 20 replications in which IND selects it. Compare against whether SO selects it. This identifies the substations whose protection depends on modeling correlation.
5. **Qualitative pattern.** Using the substation coordinates (`Latitude`/`Longitude` in `Final_Input1.csv`), check whether SO concentrates protection geographically (for example, along a corridor or around a cluster of coastal substations) while IND spreads it more thinly, or the reverse. Describe what you observe without assuming the answer in advance.

## Step 7: Optional robustness check with larger independent samples

The permutation approach uses the same number of scenarios as the original set. To confirm the result is not an artifact of the small scenario count, repeat Steps 3 to 5 for budgets {20, 40, 60} using independent sampling instead. For each substation, draw flood heights independently from its empirical marginal, generating N = 100 scenarios. Use 5 replications. Report whether VSC changes materially. Skip this step if solve times make it impractical, and tell me so.

## Deliverables

Save all outputs in a folder named `vsc_results`.

1. **Raw results.** A CSV with one row per (replication, budget) containing every quantity from Steps 3 to 5, plus solve time, gap, and status.
2. **Summary table.** A CSV and a LaTeX table (booktabs style) with one row per budget in {0, 10, 20, 30, 40, 50, 60, 70, 80}: L*_SO, L_SO(x_bar), mean L_SO(x_IND) with range, L*_WS, VSS, mean VSC with range, VMV, and the share of VSS due to correlation.
3. **Updated Figure 5.** The existing three curves (mean value solution, stochastic solution, wait-and-see solution) plus a fourth curve for the decorrelated solution evaluated on the true scenarios, shown as the mean with a shaded band for the min-to-max range across replications. Match the style of the existing figure (same budget axis, same color/marker conventions as `Bounds.ipynb`). Save as PDF and PNG.
4. **Decomposition figure.** A stacked bar chart of VSS split into VMV and VSC for each budget. Save as PDF and PNG.
5. **Decision comparison table.** A LaTeX table for budgets 20, 40, and 60 million with the Jaccard index, number of substations hardened by each model, average heights, and mean absolute height difference.
6. **Substation map (if coordinates are available).** A map of substations in I_f, marking those selected by SO and colored by the fraction of replications in which IND selects them.
7. **Validation report.** The results of every check in Step 2, the baseline reproduction from Step 1, and any flagged replications from Step 5.
8. **Summary for the rebuttal.** A short markdown file named `summary_for_rebuttal.md` that fills in these placeholders with the actual numbers:
   * VSC at the budget where it is largest, in GW and as a percentage of VSS,
   * the percentage by which the decorrelated model misestimates its own load shed, and the direction,
   * the Jaccard overlap between SO and IND selections at each of the three budgets,
   * a plain description of how the hardening patterns differ,
   * the original versus decorrelated mean Spearman correlation and mean number of simultaneously flooded substations.

## Reporting guidance

Report results honestly, whatever they turn out to be. If VSC is small for this network, say so clearly. A small value is still a meaningful finding and should be reported as such rather than overstated. Do not tune seeds, budgets, or sample sizes to make VSC look larger.

## Computational notes

1. Use the same MIP gap and time limit as the baseline for every solve so that all comparisons are consistent.
2. The main cost is 20 replications × 9 budgets = 180 SO solves (Step 3), each the same size as the original SO, plus 180 fix-and-resolve evaluation solves (Step 4) that should be substantially cheaper than a fresh SO solve since x/y are fixed. Warm starting each budget from the solution at the previous budget within a replication may help for Step 3.
3. `config.yaml` does not set Gurobi's `Threads` parameter, so by default every solve claims all available cores. Do not run replications concurrently without first setting an explicit per-model `Threads` value (e.g. total cores divided by the number of concurrent jobs) — otherwise concurrent solves will oversubscribe the machine and solve times will not be comparable to the baseline. Confirm the intended degree of parallelism with me before changing this.
4. Save results after every solve so that an interrupted run can be resumed without starting over.
5. Before the full run, do a pilot with 2 replications and budgets {20, 40, 60}, then report solve times for both Step 3 and Step 4 (including whether the fix-and-resolve approach in Step 4 is meaningfully faster than per-scenario solves) so we can decide whether to proceed with the full design.
