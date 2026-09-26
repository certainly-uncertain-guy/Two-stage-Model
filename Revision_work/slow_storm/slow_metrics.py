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
EVAL_TOL = 1e-4  # gap of the fix-and-resolve evaluations
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

    def add(check, budget, value, reference, passed, informational=False):
        rows.append({"check": check, "budget": budget, "value": value,
                     "reference": reference, "passed": bool(passed), "informational": informational})

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
            # Informational (not pass/fail): both sides are 1e-4-gap evaluations and the
            # re-solve is warm-started from x_SO, so any negative value is worth reporting.
            tight = EVAL_TOL * abs(r["L_star_slow"]) + ABS_FLOOR
            add("info: delta_mis >= 0 (re-solve beats uniform plan)", b, r["delta_mis"], 0.0,
                r["delta_mis"] >= -tight, informational=True)
            add("info: delta_rev >= 0 (else uniform baseline suboptimal)", b, r["delta_rev"], 0.0,
                r["delta_rev"] >= -tight, informational=True)

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
