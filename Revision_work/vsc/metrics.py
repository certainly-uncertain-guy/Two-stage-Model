import pandas as pd
import numpy as np


def compute_metrics(baseline_df: pd.DataFrame, eval_df: pd.DataFrame, mip_gap: float) -> pd.DataFrame:
    merged = eval_df.merge(baseline_df, on="budget", how="left")

    merged["VSC"] = merged["L_SO_xind"] - merged["L_SO_star"]
    merged["VMV"] = merged["L_SO_xbar"] - merged["L_SO_xind"]
    merged["VSS"] = merged["L_SO_xbar"] - merged["L_SO_star"]
    merged["VSC_share"] = merged["VSC"] / merged["VSS"].where(merged["VSS"] > 0)
    merged["misestimation"] = merged["L_IND_in"] - merged["L_SO_xind"]
    merged["misestimation_pct"] = 100 * merged["misestimation"] / merged["L_SO_xind"]
    merged["worst_case_gap"] = merged["worst_case_L_xind"] - merged["worst_case_L_SO"]
    merged["EVPI"] = merged["L_SO_star"] - merged["L_WS_star"]

    tolerance = mip_gap * merged["L_SO_star"].abs().clip(lower=1e-9)

    # Create a list of Python bool objects
    flags = [bool(merged["VSC"].iloc[i] < -tolerance.iloc[i]) for i in range(len(merged))]
    merged["vsc_negative_flag"] = pd.Series(flags, index=merged.index, dtype=object)

    return merged


def summarize(metrics_df: pd.DataFrame) -> pd.DataFrame:
    grouped = metrics_df.groupby("budget")
    summary = grouped.agg(
        L_SO_star=("L_SO_star", "first"),
        L_SO_xbar=("L_SO_xbar", "first"),
        L_WS_star=("L_WS_star", "first"),
        VSS=("VSS", "first"),
        L_SO_xind_mean=("L_SO_xind", "mean"),
        L_SO_xind_min=("L_SO_xind", "min"),
        L_SO_xind_max=("L_SO_xind", "max"),
        VSC_mean=("VSC", "mean"),
        VSC_min=("VSC", "min"),
        VSC_max=("VSC", "max"),
        VMV_mean=("VMV", "mean"),
        VSC_share_mean=("VSC_share", "mean"),
        n_negative_vsc_flags=("vsc_negative_flag", "sum"),
    ).reset_index()
    return summary
