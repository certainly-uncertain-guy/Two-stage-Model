"""Deliverables 1-7 of the spec: tables, figures, and the validation report.
SUMMARY.md (deliverable 8) is written by hand from these outputs."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from certainty_metrics import (compute_metrics, cross_matrix, ordering_chain,  # noqa: E402
                               summarize)
from common import WAIT_AND_SEE_JSON  # noqa: E402

GW = 10  # raw objective / 10 = GW, as in Bounds.ipynb
DECISION_BUDGETS = [20, 40, 60]
# Figure 5 colors from Bounds.ipynb, plus Okabe-Ito reddish purple for the new curve
COLORS = {"mv": "#009e73", "so": "#0072b2", "ws": "#d55e00", "cert": "#cc79a7"}


def build_metrics(out_dir: Path, baseline_df, solve_df, eval_df, mip_gap):
    with open(WAIT_AND_SEE_JSON) as f:
        ws_cache = json.load(f)
    metrics = compute_metrics(baseline_df, solve_df, eval_df, ws_cache, mip_gap)
    summary = summarize(metrics)
    chain = ordering_chain(summary, mip_gap)
    metrics.to_csv(out_dir / "raw_results.csv", index=False)
    summary.to_csv(out_dir / "summary.csv", index=False)
    return metrics, summary, chain


def _latex_table(df: pd.DataFrame, caption: str, label: str) -> str:
    cols = "l" + "r" * (df.shape[1] - 1)
    lines = [r"\begin{table}[ht]", r"\centering", rf"\caption{{{caption}}}", rf"\label{{{label}}}",
             rf"\begin{{tabular}}{{{cols}}}", r"\toprule", " & ".join(df.columns) + r" \\", r"\midrule"]
    lines += [" & ".join(str(v) for v in row) + r" \\" for row in df.itertuples(index=False)]
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines) + "\n"


def write_summary_table(out_dir: Path, summary: pd.DataFrame):
    f = lambda v: f"{v / GW:.3f}"  # noqa: E731
    t = pd.DataFrame({
        "Budget (\\$M)": summary["budget"].astype(int),
        "$L^*_{WS}$": summary["L_WS_star"].map(f),
        "$L^*_{SO}$": summary["L_SO_star"].map(f),
        "$L_{SO}(\\bar{x})$": summary["L_SO_xbar"].map(f),
        "avg. certain $\\frac{1}{|K|}\\sum_k L_{SO}(x_k)$ [min, max]": [f"{f(a)} [{f(b)}, {f(c)}]" for a, b, c in
                                          zip(summary["L_SO_xk_mean"], summary["L_SO_xk_min"],
                                              summary["L_SO_xk_max"])],
        "avg. certain $-$ $L^*_{SO}$": summary["cost_of_certainty"].map(f),
        "best $k$": summary["best_scenario"].str.replace("_", r"\_"),
        "worst $k$": summary["worst_scenario"].str.replace("_", r"\_"),
    })
    (out_dir / "summary_table.tex").write_text(_latex_table(
        t, "Expected load shed (GW) of plans built assuming certainty in one scenario, "
           "evaluated on all 16 MEOW scenarios.", "tab:certainty_summary"))


def plot_bounds(out_dir: Path, summary: pd.DataFrame):
    b = summary["budget"].values
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.plot(b, summary["L_SO_xbar"] / GW, marker="o", color=COLORS["mv"], label="Mean value solution")
    ax.plot(b, summary["L_SO_star"] / GW, marker="o", color=COLORS["so"], label="Stochastic solution")
    ax.plot(b, summary["L_WS_star"] / GW, marker="o", color=COLORS["ws"], label="Wait-and-see solution")
    ax.fill_between(b, summary["L_SO_xk_min"] / GW, summary["L_SO_xk_max"] / GW,
                    color=COLORS["cert"], alpha=0.2, linewidth=0)
    ax.plot(b, summary["L_SO_xk_mean"] / GW, marker="s", color=COLORS["cert"],
            label="Single-scenario certainty\n(mean, min–max band)")
    ax.set_xlabel("Budget in Millions ($)", fontsize=11)
    ax.set_ylabel("Load-shed (GW)", fontsize=11)
    ax.set_ylim(-0.25, 5.25)
    ax.tick_params(labelsize=11)
    ax.legend(loc=1, prop={"size": 9}, frameon=False)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"certainty_bounds.{ext}", dpi=200)
    plt.close(fig)


def plot_heatmaps(out_dir: Path, eval_df: pd.DataFrame):
    budgets = [b for b in DECISION_BUDGETS if b in set(eval_df["budget"])]
    for budget in budgets:
        mat = cross_matrix(eval_df, budget) / GW
        mat.to_csv(out_dir / f"cross_matrix_{budget}M.csv")
        fig, ax = plt.subplots(figsize=(0.45 * mat.shape[1] + 2.5, max(0.45 * mat.shape[0] + 1.5, 4)))
        im = ax.imshow(mat.values, cmap="Blues", aspect="auto", vmin=0)
        ax.set_xticks(range(mat.shape[1]), mat.columns, rotation=90, fontsize=8)
        ax.set_yticks(range(mat.shape[0]), mat.index, fontsize=8)
        for r, name in enumerate(mat.index):  # outline L(x_k, k): planned-for scenario occurs
            if name in mat.columns:
                c = list(mat.columns).index(name)
                ax.add_patch(plt.Rectangle((c - 0.5, r - 0.5), 1, 1, fill=False, edgecolor="#333333", lw=1.2))
        ax.set_xlabel("Scenario that occurs")
        ax.set_ylabel("Scenario planned for (certain)")
        ax.set_title(f"Load shed L(x_k, k') in GW, budget ${budget}M", fontsize=10)
        fig.colorbar(im, ax=ax, label="GW")
        fig.tight_layout()
        for ext in ("pdf", "png"):
            fig.savefig(out_dir / f"cross_heatmap_{budget}M.{ext}", dpi=200)
        plt.close(fig)
    # every budget's matrix as CSV, not only the plotted ones
    for budget in sorted(set(eval_df["budget"]) - set(budgets)):
        (cross_matrix(eval_df, budget) / GW).to_csv(out_dir / f"cross_matrix_{budget}M.csv")


def _fmt_nanmean(values) -> str:
    finite = [v for v in values if not np.isnan(v)]
    return f"{np.mean(finite):.2f}" if finite else "--"


def write_decision_comparison(out_dir: Path, baseline_df, solve_df):
    from decisions import budget_allocation, jaccard_index, mean_abs_height_diff, selection_frequency

    subs = [c[len("x_SO__"):] for c in baseline_df.columns if c.startswith("x_SO__")]
    rows, freq_frames = [], []
    for budget in [b for b in DECISION_BUDGETS if b in set(solve_df["budget"])]:
        base = baseline_df[baseline_df["budget"] == budget].iloc[0]
        x_so = {s: base[f"x_SO__{s}"] for s in subs}
        plans = {r["scenario"]: {s: r[f"x_tb__{s}"] for s in subs}
                 for _, r in solve_df[solve_df["budget"] == budget].iterrows()}
        spend = solve_df[solve_df["budget"] == budget]["spend_tb"] / (budget * 1e6)
        jac = [jaccard_index(x_so, x) for x in plans.values()]
        alloc = [budget_allocation(x) for x in plans.values()]
        so_alloc = budget_allocation(x_so)
        rows.append({
            "Budget (\\$M)": budget,
            "SO hardened": so_alloc["n_hardened"],
            "SO mean height": f"{so_alloc['mean_height']:.2f}",
            "$x_k$ hardened (mean)": f"{np.mean([a['n_hardened'] for a in alloc]):.1f}",
            "$x_k$ mean height": f"{np.mean([a['mean_height'] for a in alloc]):.2f}",
            "Jaccard vs SO mean [min, max]": f"{np.mean(jac):.2f} [{min(jac):.2f}, {max(jac):.2f}]",
            "mean abs height diff": _fmt_nanmean([mean_abs_height_diff(x_so, x) for x in plans.values()]),
            "budget used (mean)": f"{100 * spend.mean():.0f}\\%",
        })
        freq = selection_frequency(plans).rename("certain_selection_freq").to_frame()
        freq["SO_selected"] = [round(x_so.get(s, 0)) > 0 for s in freq.index]
        freq.insert(0, "budget", budget)
        freq_frames.append(freq[(freq["certain_selection_freq"] > 0) | freq["SO_selected"]])
    if not rows:
        return
    (out_dir / "decision_comparison.tex").write_text(_latex_table(
        pd.DataFrame(rows), "Hardening decisions of the stochastic plan vs. single-scenario certain plans.",
        "tab:certainty_decisions"))
    pd.concat(freq_frames).rename_axis("substation").to_csv(out_dir / "selection_frequency.csv")


def write_validation_report(out_dir: Path, metrics: pd.DataFrame, summary: pd.DataFrame,
                            chain: pd.DataFrame, baseline_df: pd.DataFrame):
    L = ["# Validation report: single-scenario certainty experiment", ""]
    L += ["## Baseline (L*_SO from output/sm_16 Gurobi logs)", "",
          "| budget | L*_SO | final gap | L*_SO (stochastic_solution.csv) | L_SO(x̄) | L*_WS |",
          "|---|---|---|---|---|---|"]
    for _, r in baseline_df.iterrows():
        L.append(f"| {r['budget']} | {r['L_SO_star']:.4f} | {100 * r['L_SO_star_gap']:.2f}% | "
                 f"{r['L_SO_star_csv']} | {r['L_SO_xbar']:.4f} | {r['L_WS_star']:.4f} |")
    L += ["", "Values in raw model units (divide by 10 for GW).", ""]

    L += ["## Wait-and-see cache match (decision step == WS subproblem)", ""]
    bad = metrics[~metrics["ws_match"]]
    L.append(f"{len(metrics) - len(bad)}/{len(metrics)} solves match `wait_and_see_dict.json` within the MIP gap.")
    for _, r in bad.iterrows():
        L.append(f"- MISMATCH {r['scenario']} ${r['budget']}M: L_in={r['L_in']:.4f} cache={r['ws_cache']:.4f}")
    L.append("")

    L += ["## Cross-matrix diagonal L(x_k, k) vs L_in", ""]
    bad = metrics[~metrics["diag_match"]]
    L.append(f"{len(metrics) - len(bad)}/{len(metrics)} diagonals match within tolerance "
             f"(max |diff| = {metrics['diag_diff'].abs().max():.4f}).")
    for _, r in bad.iterrows():
        L.append(f"- MISMATCH {r['scenario']} ${r['budget']}M: diag={r['L_diag']:.4f} L_in={r['L_in']:.4f}")
    L.append("")

    L += ["## Ordering chain L*_WS ≤ L*_SO ≤ min_k L_SO(x_k) ≤ mean_k L_SO(x_k)", "",
          "```", chain.to_string(index=False), "```",
          "", "`mean_L_in_eq_ws` is only checked when all 16 scenarios ran (NA otherwise).", ""]

    L += ["## Negative regret beyond the baseline's own gap", ""]
    bad = metrics[metrics["regret_flag"]]
    L.append("None." if bad.empty else "")
    for _, r in bad.iterrows():
        L.append(f"- {r['scenario']} ${r['budget']}M: L_SO(x_k)={r['L_SO_xk']:.4f} < L*_SO={r['L_SO_star']:.4f} "
                 f"(baseline gap {100 * r['L_SO_star_gap']:.2f}%)")
    L.append("")

    L += ["## Effect of the minimum-spend tie-break", ""]
    changed = metrics[metrics["tie_break_effect"].abs() > 1e-4]
    L.append(f"The tie-break changed L_SO(x_k) in {len(changed)}/{len(metrics)} (scenario, budget) pairs.")
    for _, r in changed.iterrows():
        L.append(f"- {r['scenario']} ${r['budget']}M: raw={r['L_SO_xk_raw']:.4f} tie-broken={r['L_SO_xk']:.4f} "
                 f"(spend raw={r['spend_raw'] / 1e6:.2f}M, tie-broken={r['spend_tb'] / 1e6:.2f}M)")
    L.append("")
    (out_dir / "validation_report.md").write_text("\n".join(L))


def build_report(out_dir: Path, baseline_df, solve_df, eval_df, mip_gap):
    metrics, summary, chain = build_metrics(out_dir, baseline_df, solve_df, eval_df, mip_gap)
    write_summary_table(out_dir, summary)
    plot_bounds(out_dir, summary)
    plot_heatmaps(out_dir, eval_df)
    write_decision_comparison(out_dir, baseline_df, solve_df)
    write_validation_report(out_dir, metrics, summary, chain, baseline_df)
    return metrics, summary, chain
