import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from certainty_metrics import (compute_metrics, cross_matrix, ordering_chain,
                               parse_gurobi_log, summarize)
from common import single_scenario_input1

SCEN = ["a", "b"]


def _baseline(L_so=3.0, gap=0.0):
    return pd.DataFrame({"budget": [20], "L_SO_star": [L_so], "L_SO_star_gap": [gap],
                         "L_SO_xbar": [5.0], "L_WS_star": [1.5], "worst_case_L_SO": [4.0]})


def _solve():
    return pd.DataFrame({"scenario": SCEN, "scenario_col": [f"max_flood_level_{s}" for s in SCEN],
                         "budget": [20, 20], "L_in": [1.0, 2.0], "spend_raw": [1e7, 2e7],
                         "spend_tb": [1e7, 1.5e7], "x_tb__1": [3, 0]})


def _eval(L_a=3.5, L_b=4.0):
    # rows: plan built for a / b; L__<k'>: load shed when k' occurs
    tb = pd.DataFrame({"scenario": SCEN, "budget": [20, 20], "variant": ["tb", "tb"],
                       "L_SO_xk": [L_a, L_b], "worst_case_L_xk": [6.0, 6.0],
                       "L__a": [1.0, 2.0], "L__b": [6.0, 6.0]})
    raw = tb.assign(variant="raw", L_SO_xk=[L_a, L_b + 0.5])
    return pd.concat([tb, raw], ignore_index=True)


WS = {"20": {"max_flood_level_a": 1.0, "max_flood_level_b": 2.0}}


def test_compute_metrics_quantities():
    m = compute_metrics(_baseline(), _solve(), _eval(), WS, mip_gap=0.005).set_index("scenario")
    assert m.loc["a", "regret"] == 3.5 - 3.0
    assert m.loc["b", "overconfidence"] == 4.0 - 2.0
    assert m.loc["a", "worst_case_gap"] == 6.0 - 4.0
    assert m.loc["b", "vs_mean_value"] == 4.0 - 5.0
    assert m.loc["b", "tie_break_effect"] == 0.5
    assert m.loc["a", "tie_break_effect"] == 0.0
    assert m.loc["a", "ws_match"] and m.loc["b", "ws_match"]
    assert m.loc["a", "L_diag"] == 1.0  # L(x_a, a)
    assert m.loc["b", "L_diag"] == 6.0  # L(x_b, b)
    assert "x_tb__1" not in m.columns


def test_regret_flag_respects_baseline_gap():
    # L_SO(x_a)=2.9 < L*_SO=3.0: legitimate if baseline gap is 5%, a flag at 0%
    ev = _eval(L_a=2.9)
    loose = compute_metrics(_baseline(gap=0.05), _solve(), ev, WS, mip_gap=0.005).set_index("scenario")
    tight = compute_metrics(_baseline(gap=0.0), _solve(), ev, WS, mip_gap=0.005).set_index("scenario")
    assert not loose.loc["a", "regret_flag"]
    assert tight.loc["a", "regret_flag"]


def test_ws_mismatch_detected():
    ws = {"20": {"max_flood_level_a": 1.5, "max_flood_level_b": 2.0}}
    m = compute_metrics(_baseline(), _solve(), _eval(), ws, mip_gap=0.005).set_index("scenario")
    assert not m.loc["a", "ws_match"]
    assert m.loc["b", "ws_match"]


def test_summarize_and_ordering_chain():
    m = compute_metrics(_baseline(), _solve(), _eval(), WS, mip_gap=0.005)
    s = summarize(m)
    row = s.iloc[0]
    assert row["L_SO_xk_mean"] == 3.75
    assert row["cost_of_certainty"] == 3.75 - 3.0
    assert abs(row["cost_of_certainty_pct"] - 25.0) < 1e-9
    assert row["best_scenario"] == "a" and row["worst_scenario"] == "b"
    assert row["mean_L_in"] == 1.5
    assert row["n_tie_break_changed"] == 1
    c = ordering_chain(s, mip_gap=0.005, n_total_scenarios=2).iloc[0]
    assert c["ws_le_so"] and c["so_le_min_xk"] and c["min_le_mean_xk"]
    assert c["mean_L_in_eq_ws"]
    # a partial (pilot) run leaves the WS-mean check undetermined
    assert pd.isna(ordering_chain(s, mip_gap=0.005, n_total_scenarios=16).iloc[0]["mean_L_in_eq_ws"])


def test_ordering_chain_catches_violation():
    m = compute_metrics(_baseline(L_so=3.8), _solve(), _eval(), WS, mip_gap=0.005)
    c = ordering_chain(summarize(m), mip_gap=0.005, n_total_scenarios=2).iloc[0]
    assert not c["so_le_min_xk"]  # min_k L_SO(x_k)=3.5 < L*_SO=3.8 with 0% baseline gap


def test_cross_matrix_orientation():
    mat = cross_matrix(_eval(), 20)
    assert list(mat.index) == ["a", "b"] and list(mat.columns) == ["a", "b"]
    assert mat.loc["b", "a"] == 2.0  # planned for b, a occurs


def test_single_scenario_input1_keeps_positions():
    df = pd.DataFrame({"BusNum": [1, 2], "BusName": ["x", "y"], "SubNum": [7, 8], "SubName": ["p", "q"],
                       "Latitude": [0, 0], "Longitude": [0, 0], "generation_capacity_min": [0, 0],
                       "generation_capacity_max": [1, 1], "load": [5, 6],
                       "max_flood_level_a": [1, 0], "max_flood_level_b": [2, 3]})
    out = single_scenario_input1(df, "max_flood_level_b")
    assert list(out.columns)[:9] == list(df.columns)[:9]
    assert [c for c in out.columns if c.startswith("max")] == ["max_flood_level_b"]
    assert out.iloc[:, 8].tolist() == [5, 6]
    assert out["max_flood_level_b"].tolist() == [2, 3]


def test_parse_gurobi_log(tmp_path=None):
    import tempfile
    d = Path(tmp_path or tempfile.mkdtemp())
    p = d / "20M"
    p.write_text("Time limit reached\nBest objective 1.374452649386e+01, best bound 1.309748766002e+01, "
                 "gap 4.7076%\n")
    obj, gap = parse_gurobi_log(p)
    assert abs(obj - 13.74452649386) < 1e-9
    assert abs(gap - 0.047076) < 1e-9


def test_scenario_subset_input1_keeps_order_and_positions():
    from common import scenario_subset_input1
    df = pd.DataFrame({"BusNum": [1], "BusName": ["x"], "SubNum": [7], "SubName": ["p"],
                       "Latitude": [0], "Longitude": [0], "generation_capacity_min": [0],
                       "generation_capacity_max": [1], "load": [5],
                       "max_flood_level_a": [1], "max_flood_level_b": [2], "max_flood_level_c": [3]})
    out = scenario_subset_input1(df, ["max_flood_level_c", "max_flood_level_a"])
    assert list(out.columns)[:9] == list(df.columns)[:9]
    assert [c for c in out.columns if c.startswith("max")] == ["max_flood_level_c", "max_flood_level_a"]
    assert out["max_flood_level_c"].tolist() == [3]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("All certainty tests passed.")
