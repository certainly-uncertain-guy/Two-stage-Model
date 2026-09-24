import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from metrics import compute_metrics, summarize


def test_compute_metrics_basic_decomposition():
    baseline_df = pd.DataFrame({
        "budget": [20],
        "L_SO_star": [3.0],
        "L_SO_xbar": [5.0],
        "L_WS_star": [1.0],
        "worst_case_L_SO": [4.0],
    })
    eval_df = pd.DataFrame({
        "replication": [1],
        "budget": [20],
        "L_SO_xind": [3.8],
        "worst_case_L_xind": [4.5],
        "L_IND_in": [3.5],
    })
    out = compute_metrics(baseline_df, eval_df, mip_gap=0.005)
    row = out.iloc[0]
    assert row["VSC"] == 3.8 - 3.0
    assert row["VMV"] == 5.0 - 3.8
    assert row["VSS"] == 5.0 - 3.0
    assert abs(row["VMV"] + row["VSC"] - row["VSS"]) < 1e-9
    assert row["misestimation"] == 3.5 - 3.8
    assert row["worst_case_gap"] == 4.5 - 4.0
    assert row["EVPI"] == 3.0 - 1.0


def test_negative_vsc_beyond_gap_is_flagged():
    baseline_df = pd.DataFrame({
        "budget": [20], "L_SO_star": [3.0], "L_SO_xbar": [5.0],
        "L_WS_star": [1.0], "worst_case_L_SO": [4.0],
    })
    eval_df = pd.DataFrame({
        "replication": [1], "budget": [20],
        "L_SO_xind": [2.5],  # below L_SO_star -> VSC negative beyond a 0.005 gap
        "worst_case_L_xind": [4.0], "L_IND_in": [2.5],
    })
    out = compute_metrics(baseline_df, eval_df, mip_gap=0.005)
    assert out.iloc[0]["vsc_negative_flag"] is True


def test_summarize_aggregates_across_replications():
    baseline_df = pd.DataFrame({
        "budget": [20, 20], "L_SO_star": [3.0, 3.0], "L_SO_xbar": [5.0, 5.0],
        "L_WS_star": [1.0, 1.0], "worst_case_L_SO": [4.0, 4.0],
    })
    eval_df = pd.DataFrame({
        "replication": [1, 2], "budget": [20, 20],
        "L_SO_xind": [3.5, 4.0], "worst_case_L_xind": [4.2, 4.4],
        "L_IND_in": [3.4, 3.9],
    })
    metrics_df = compute_metrics(baseline_df, eval_df, mip_gap=0.005)
    summary = summarize(metrics_df)
    row = summary.iloc[0]
    assert row["VSC_mean"] == ((3.5 - 3.0) + (4.0 - 3.0)) / 2
    assert row["VSC_min"] == 3.5 - 3.0
    assert row["VSC_max"] == 4.0 - 3.0


if __name__ == "__main__":
    test_compute_metrics_basic_decomposition()
    test_negative_vsc_beyond_gap_is_flagged()
    test_summarize_aggregates_across_replications()
    print("All metrics.py tests passed.")
