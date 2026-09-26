"""Pure-pandas metrics for the certainty experiment (Step 4 of the spec).

Objective values are in the model's raw units (per-unit load, 100 MW);
divide by 10 for GW, as Bounds.ipynb does.
"""
import re
from pathlib import Path

import pandas as pd

ABS_FLOOR = 1e-4
_BEST_RE = re.compile(r"Best objective ([-+0-9.eE]+), best bound ([-+0-9.eE]+), gap ([-+0-9.eE]+)%")


def tolerance(value: float, gap: float) -> float:
    return gap * abs(value) + ABS_FLOOR


def parse_gurobi_log(log_path: Path) -> tuple:
    """(best objective, final relative gap) from the last 'Best objective' line
    of a Gurobi log."""
    matches = _BEST_RE.findall(Path(log_path).read_text())
    if not matches:
        raise ValueError(f"no 'Best objective' line in {log_path}")
    obj, _, gap_pct = matches[-1]
    return float(obj), float(gap_pct) / 100


def compute_metrics(baseline_df: pd.DataFrame, solve_df: pd.DataFrame, eval_df: pd.DataFrame,
                    ws_cache: dict, mip_gap: float) -> pd.DataFrame:
    """One row per (scenario, budget).

    baseline_df: budget, L_SO_star, L_SO_star_gap, L_SO_xbar, L_WS_star, worst_case_L_SO
    solve_df:    scenario, scenario_col, budget, L_in, spend_tb, n_hardened_tb, ...
    eval_df:     scenario, budget, variant ('tb'/'raw'), L_SO_xk, worst_case_L_xk, L__<scenario'>...
    ws_cache:    wait_and_see_dict.json contents, {str(budget): {scenario_col: value}}
    """
    shed_cols = [c for c in eval_df.columns if c.startswith("L__")]
    n_scen_eval = len(shed_cols)

    tb = eval_df[eval_df["variant"] == "tb"][["scenario", "budget", "L_SO_xk", "worst_case_L_xk"] + shed_cols]
    raw = eval_df[eval_df["variant"] == "raw"][["scenario", "budget", "L_SO_xk"]].rename(
        columns={"L_SO_xk": "L_SO_xk_raw"})

    keep = [c for c in solve_df.columns if not c.startswith("x_")]
    m = (solve_df[keep]
         .merge(tb, on=["scenario", "budget"], how="inner")
         .merge(raw, on=["scenario", "budget"], how="left")
         .merge(baseline_df, on="budget", how="left"))

    m["regret"] = m["L_SO_xk"] - m["L_SO_star"]
    m["regret_pct"] = 100 * m["regret"] / m["L_SO_star"].where(m["L_SO_star"].abs() > ABS_FLOOR)
    m["overconfidence"] = m["L_SO_xk"] - m["L_in"]
    m["overconfidence_pct"] = 100 * m["overconfidence"] / m["L_SO_xk"].where(m["L_SO_xk"].abs() > ABS_FLOOR)
    m["worst_case_gap"] = m["worst_case_L_xk"] - m["worst_case_L_SO"]
    m["vs_mean_value"] = m["L_SO_xk"] - m["L_SO_xbar"]
    m["tie_break_effect"] = m["L_SO_xk_raw"] - m["L_SO_xk"]

    # L*_SO is only an upper bound where the baseline hit its time limit
    # (e.g. 4.7% gap at $20M), so a certain plan may legitimately beat it
    # there. Flag only regret below what the baseline's own gap allows.
    baseline_gap = m["L_SO_star_gap"].clip(lower=mip_gap)
    m["regret_flag"] = m["regret"] < -(baseline_gap * m["L_SO_star"].abs() + ABS_FLOOR)

    # Decision step == wait-and-see subproblem, so L_in must match the cache.
    m["ws_cache"] = [ws_cache[str(int(b))][c] for b, c in zip(m["budget"], m["scenario_col"])]
    m["ws_diff"] = m["L_in"] - m["ws_cache"]
    m["ws_match"] = m["ws_diff"].abs() <= mip_gap * m[["L_in", "ws_cache"]].abs().max(axis=1) + ABS_FLOOR

    # Diagonal L(x_k, k) of the cross matrix vs L_in. The evaluation's gap is
    # on the 16-scenario average, so one scenario may be off by up to
    # n_scen * gap * L_SO_xk.
    m["L_diag"] = [row[f"L__{row['scenario']}"] for _, row in m.iterrows()]
    m["diag_diff"] = m["L_diag"] - m["L_in"]
    m["diag_match"] = m["diag_diff"].abs() <= (
        mip_gap * (m["L_in"].abs() + n_scen_eval * m["L_SO_xk"].abs()) + ABS_FLOOR)
    return m


def summarize(metrics_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for budget, g in metrics_df.groupby("budget"):
        best = g.loc[g["L_SO_xk"].idxmin()]
        worst = g.loc[g["L_SO_xk"].idxmax()]
        rows.append({
            "budget": budget,
            "n_scenarios": len(g),
            "L_WS_star": g["L_WS_star"].iloc[0],
            "mean_L_in": g["L_in"].mean(),
            "L_SO_star": g["L_SO_star"].iloc[0],
            "L_SO_star_gap": g["L_SO_star_gap"].iloc[0],
            "L_SO_xbar": g["L_SO_xbar"].iloc[0],
            "L_SO_xk_mean": g["L_SO_xk"].mean(),
            "L_SO_xk_min": g["L_SO_xk"].min(),
            "L_SO_xk_max": g["L_SO_xk"].max(),
            "regret_mean": g["regret"].mean(),
            # Headline: average-of-averages of the certain plans vs. planning under
            # uncertainty. Equals regret_mean; named for the comparison it makes.
            "cost_of_certainty": g["L_SO_xk"].mean() - g["L_SO_star"].iloc[0],
            "cost_of_certainty_pct": (100 * (g["L_SO_xk"].mean() - g["L_SO_star"].iloc[0])
                                      / g["L_SO_star"].iloc[0] if abs(g["L_SO_star"].iloc[0]) > ABS_FLOOR
                                      else float("nan")),
            "overconfidence_mean": g["overconfidence"].mean(),
            "worst_case_L_SO": g["worst_case_L_SO"].iloc[0],
            "worst_case_L_xk_mean": g["worst_case_L_xk"].mean(),
            "best_scenario": best["scenario"],
            "worst_scenario": worst["scenario"],
            "n_regret_flags": int(g["regret_flag"].sum()),
            "n_ws_mismatch": int((~g["ws_match"]).sum()),
            "n_diag_mismatch": int((~g["diag_match"]).sum()),
            "n_tie_break_changed": int((g["tie_break_effect"].abs() > ABS_FLOOR).sum()),
        })
    return pd.DataFrame(rows)


def ordering_chain(summary: pd.DataFrame, mip_gap: float, n_total_scenarios: int = 16) -> pd.DataFrame:
    """Checks L*_WS <= L*_SO <= min_k L_SO(x_k) <= mean_k L_SO(x_k), and that
    mean_k L_in reproduces L*_WS (only meaningful when all scenarios ran)."""
    out = summary[["budget"]].copy()
    so_tol = summary["L_SO_star_gap"].clip(lower=mip_gap) * summary["L_SO_star"].abs() + ABS_FLOOR
    out["ws_le_so"] = summary["L_WS_star"] <= summary["L_SO_star"] + so_tol
    out["so_le_min_xk"] = summary["L_SO_star"] <= summary["L_SO_xk_min"] + so_tol
    out["min_le_mean_xk"] = summary["L_SO_xk_min"] <= summary["L_SO_xk_mean"] + ABS_FLOOR
    full = summary["n_scenarios"] == n_total_scenarios
    ws_ok = (summary["mean_L_in"] - summary["L_WS_star"]).abs() <= [
        tolerance(v, mip_gap) for v in summary["L_WS_star"]]
    out["mean_L_in_eq_ws"] = ws_ok.where(full, other=pd.NA)
    return out


def cross_matrix(eval_df: pd.DataFrame, budget, variant: str = "tb") -> pd.DataFrame:
    """16 x 16 matrix of L(x_k, k'): rows = scenario planned for, columns =
    scenario that occurs, in eval_df's scenario-column order."""
    shed_cols = [c for c in eval_df.columns if c.startswith("L__")]
    sel = eval_df[(eval_df["budget"] == budget) & (eval_df["variant"] == variant)]
    mat = sel.set_index("scenario")[shed_cols]
    mat.columns = [c[len("L__"):] for c in shed_cols]
    order = [c for c in mat.columns if c in mat.index]
    return mat.loc[order + [r for r in mat.index if r not in order]]
