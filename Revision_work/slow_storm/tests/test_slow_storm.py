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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("All slow-storm tests passed.")
