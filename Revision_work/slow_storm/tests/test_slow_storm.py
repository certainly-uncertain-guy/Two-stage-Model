import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from storm_weights import parse_scenario, slow_shift_weights, weighted_loss

DIRS = ["w", "wnw", "nw", "nnw"]
SPEEDS = ["05", "10", "15", "25"]
SCEN = [f"{d}_5_{s}" for d in DIRS for s in SPEEDS]


def test_parse_scenario_accepts_full_and_short_names():
    assert parse_scenario("max_flood_level_wnw_5_25") == ("wnw", "5", "25")
    assert parse_scenario("nw_5_05") == ("nw", "5", "05")


def test_slow_shift_weights_lambda_zero_is_uniform():
    w = slow_shift_weights(SCEN, 0.0)
    assert list(w.index) == SCEN
    assert all(abs(v - 1 / 16) < 1e-12 for v in w)


def test_slow_shift_weights_lambda_one():
    w = slow_shift_weights(["max_flood_level_" + s for s in SCEN], 1.0)
    assert abs(w.sum() - 1) < 1e-12
    assert abs(w["w_5_05"] - 2 / 16) < 1e-12 and w["w_5_25"] == 0
    assert abs(w["nnw_5_10"] - 1 / 16) < 1e-12 and abs(w["nnw_5_15"] - 1 / 16) < 1e-12
    for d in DIRS:  # direction marginals unchanged
        assert abs(w[[f"{d}_5_{s}" for s in SPEEDS]].sum() - 0.25) < 1e-12


def test_slow_shift_weights_partial_lambda():
    w = slow_shift_weights(SCEN, 0.5)
    assert abs(w["wnw_5_05"] - 1.5 / 16) < 1e-12 and abs(w["wnw_5_25"] - 0.5 / 16) < 1e-12


def test_slow_shift_weights_rejects_bad_input():
    for bad_lam in (-0.1, 1.1):
        try:
            slow_shift_weights(SCEN, bad_lam)
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
    try:
        slow_shift_weights([s for s in SCEN if s != "w_5_25"], 1.0)
        raise AssertionError("expected ValueError for missing speed-25 partner")
    except ValueError:
        pass


def test_weighted_loss_ignores_zero_weight():
    vec = pd.Series({s: (100.0 if s.endswith("25") else 1.0) for s in SCEN})
    assert abs(weighted_loss(vec, slow_shift_weights(SCEN, 1.0)) - 1.0) < 1e-12
    assert abs(weighted_loss(vec, slow_shift_weights(SCEN, 0.0)) - (12 + 400) / 16) < 1e-12


from slow_metrics import (budget_table, build_summary, lambda_curves, near_optimal_budget,
                          substation_changes, validation_checks)


def _vectors():
    rows = []
    # SO: speed-25 scenarios cost 2, others 1; RO: flat 1.5; MV: flat 3; SLOW: 05 costs 0.5, 25 costs 4
    spec = {"SO": lambda s: 2.0 if s.endswith("25") else 1.0,
            "RO": lambda s: 1.5,
            "MV": lambda s: 3.0,
            "SLOW": lambda s: 4.0 if s.endswith("25") else (0.5 if s.endswith("05") else 1.0)}
    for plan, f in spec.items():
        row = {"plan": plan, "budget": 20}
        row.update({f"L__{s}": f(s) for s in SCEN})
        rows.append(row)
    return pd.DataFrame(rows)


def _baseline():
    return pd.DataFrame({"budget": [20], "L_SO_star": [1.25], "L_SO_star_gap": [0.0], "L_SO_xbar": [3.0],
                         "x_SO__1": [3.0], "x_SO__2": [0.0]})


def _slow_df(obj=0.9):
    return pd.DataFrame({"budget": [20], "L_star_slow_solver": [obj], "gap": [0.0],
                         "x__1": [0.0], "x__2": [4.0]})


WS = {"20": {f"max_flood_level_{s}": 0.2 for s in SCEN}}


def test_build_summary_quantities():
    s = build_summary(_vectors(), _slow_df(), _baseline(), pd.Series({20: 1.6}), WS).iloc[0]
    assert abs(s["L0_xSO"] - (12 * 1 + 4 * 2) / 16) < 1e-12        # 1.25
    assert abs(s["L_slow_xSO"] - 1.0) < 1e-12                      # speed-25 weight is 0
    # SLOW under p_slow: 4 dirs x (2/16*0.5 + 2*1/16*1) = 0.75
    assert abs(s["L_star_slow"] - 0.75) < 1e-12
    assert abs(s["delta_mis"] - 0.25) < 1e-12
    assert abs(s["L0_xslow"] - (4 * (0.5 + 1 + 1 + 4)) / 16) < 1e-12
    assert abs(s["delta_rev"] - (s["L0_xslow"] - s["L0_xSO"])) < 1e-12
    assert abs(s["WS_slow"] - 0.2) < 1e-12
    assert s["max_xRO"] == 1.5 and s["L_RO_star"] == 1.6


def test_build_summary_without_slow_rows_gives_nan():
    v = _vectors()
    s = build_summary(v[v["plan"] != "SLOW"], _slow_df().iloc[0:0], _baseline(), pd.Series({20: 1.6}), WS).iloc[0]
    assert pd.isna(s["L_star_slow"]) and pd.isna(s["delta_mis"])


def test_lambda_curves_interpolate():
    c = lambda_curves(_vectors(), [0.0, 0.5, 1.0]).set_index(["plan", "lam"])["L"]
    assert abs(c[("SO", 0.0)] - 1.25) < 1e-12 and abs(c[("SO", 1.0)] - 1.0) < 1e-12
    assert abs(c[("SO", 0.5)] - 1.125) < 1e-12  # linear in lambda
    assert abs(c[("RO", 0.5)] - 1.5) < 1e-12


def test_near_optimal_budget_picks_min_total_cost():
    curve = pd.Series({20: 1.0, 0: 5.0, 10: 2.0})  # unsorted on purpose
    # multiplier = 10*12*1000*100 = 12e6 $ per raw unit
    b, cost = near_optimal_budget(curve, gamma=10, restoration_h=12, voll=1000)
    assert b == 20 and abs(cost - (20e6 + 12e6)) < 1e-6


def test_near_optimal_budget_ties_pick_smallest():
    curve = pd.Series({0: 1.0, 10: 0.5})
    # multiplier 20e6 -> cost(0) = 20e6, cost(10) = 10e6 + 10e6 = 20e6
    b, _ = near_optimal_budget(curve, gamma=10, restoration_h=20, voll=1000)
    assert b == 0


def test_budget_table_regret_of_uniform_budget():
    summ = pd.DataFrame({"budget": [0, 10], "L_SO_star": [5.0, 1.0], "L0_xSO": [5.0, 1.0],
                         "L_star_slow": [6.0, 0.5], "L_slow_xSO": [6.0, 2.0]})
    t = budget_table(summ, gamma=10, restoration_hours=[12], volls=[1000]).iloc[0]
    assert t["I_uniform"] == 10 and t["I_slow"] == 10
    assert abs(t["cost_uniform_plan_under_slow"] - (10e6 + 12e6 * 2.0)) < 1e-6
    assert abs(t["regret_usd"] - (12e6 * 2.0 - 12e6 * 0.5)) < 1e-6


def test_validation_flags_slow_not_better_than_so():
    v = _vectors()
    v.loc[v["plan"] == "SLOW", [f"L__{s}" for s in SCEN]] = 1.2  # SLOW worse than SO under p_slow
    summ = build_summary(v, _slow_df(obj=1.2), _baseline(), pd.Series({20: 1.6}), WS)
    checks = validation_checks(summ, lambda_curves(v, [0.0, 1.0]), pd.Series({20: 1.5}), mip_gap=0.005)
    row = checks[checks["check"] == "L*_slow <= L_slow(x_SO)"].iloc[0]
    assert not row["passed"]


def test_validation_passes_on_consistent_data():
    v = _vectors()
    summ = build_summary(v, _slow_df(obj=0.75), _baseline(), pd.Series({20: 1.6}), WS)
    checks = validation_checks(summ, lambda_curves(v, [0.0, 0.5, 1.0]), pd.Series({20: 1.5}), mip_gap=0.005)
    failed = checks[~checks["passed"]]
    # MV flat 3.0 == L_SO_xbar 3.0; RO mean 1.5 == csv 1.5; RO max 1.5 <= 1.6
    assert failed.empty, failed.to_string()


def test_substation_changes_classifies():
    flood = pd.DataFrame({s: [0.0, 6.0, 2.0] if s.endswith("05") else [3.0, 0.0, 2.0] for s in SCEN},
                         index=["1", "2", "3"])
    out = substation_changes({"1": 3, "2": 0, "3": 2}, {"1": 0, "2": 4, "3": 2}, flood).set_index("substation")
    assert out.loc["1", "change"] == "dropped" and out.loc["2", "change"] == "added"
    assert "3" not in out.index
    assert out.loc["2", "mean_flood_05"] == 6.0 and out.loc["2", "mean_flood_25"] == 0.0


def test_validation_informs_small_negative_delta_mis():
    v = _vectors()
    v.loc[v["plan"] == "SLOW", [f"L__{s}" for s in SCEN]] = 1.002  # 0.2% worse than SO under p_slow
    summ = build_summary(v, _slow_df(obj=1.002), _baseline(), pd.Series({20: 1.6}), WS)
    checks = validation_checks(summ, lambda_curves(v, [0.0, 1.0]), pd.Series({20: 1.5}), mip_gap=0.005)
    gated = checks[checks["check"] == "L*_slow <= L_slow(x_SO)"].iloc[0]
    info = checks[checks["check"] == "info: delta_mis >= 0 (re-solve beats uniform plan)"].iloc[0]
    assert gated["passed"] and not gated["informational"]  # within the spec's gap tolerance
    assert not info["passed"] and info["informational"]


def test_validation_informs_negative_delta_rev():
    v = _vectors()
    v.loc[v["plan"] == "SLOW", [f"L__{s}" for s in SCEN]] = 0.9  # better than SO even under uniform weights
    summ = build_summary(v, _slow_df(obj=0.9), _baseline(), pd.Series({20: 1.6}), WS)
    checks = validation_checks(summ, lambda_curves(v, [0.0, 1.0]), pd.Series({20: 1.5}), mip_gap=0.005)
    info = checks[checks["check"] == "info: delta_rev >= 0 (else uniform baseline suboptimal)"].iloc[0]
    assert not info["passed"] and info["informational"]
    assert checks.loc[checks["informational"], "check"].str.startswith("info:").all()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("All slow-storm tests passed.")
