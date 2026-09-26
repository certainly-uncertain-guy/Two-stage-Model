"""Deliverables of the slow-storm spec: tables, figures A/B/C, validation report.
SUMMARY.md is written by hand from these outputs."""
import json
from pathlib import Path

from slow_paths import RM16_OUTPUT_DIR, WAIT_AND_SEE_JSON, flood_columns, short_name  # sys.path wiring first

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from certainty_metrics import parse_gurobi_log  # noqa: E402
from certainty_report import _latex_table  # noqa: E402
from slow_metrics import (budget_table, build_summary, lambda_curves, substation_changes,  # noqa: E402
                          validation_checks)

GW = 10
FENCE = "`" * 3  # markdown code fence, built so this file can live inside a fenced plan
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
        ax.set_ylim(0, 1.15 * srow.loc[b, "L_RO_star"] / GW)  # zero baseline: show effect size honestly
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
    L += ["", "## Failed checks", "", "None." if bad.empty else f"{FENCE}\n{bad.to_string(index=False)}\n{FENCE}"]
    L += ["", "## All checks", "", FENCE, checks.to_string(index=False), FENCE]
    L += ["", "## Summary (raw units; divide by 10 for GW)", "", FENCE, s.to_string(index=False), FENCE]
    if bt is not None:
        L += ["", "## Near-optimal budget", "", FENCE, bt.to_string(index=False), FENCE]
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
