import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from decorrelate import flooded_substations, build_decorrelated_flood_df, validate_decorrelation


def _toy_input1():
    # 2 substations, 2 buses each, 4 scenarios. Substation 20 never floods.
    return pd.DataFrame({
        "SubNum":   [10, 10, 20, 20],
        "max_flood_level_a": [5.0, 5.0, 0.0, 0.0],
        "max_flood_level_b": [0.0, 0.0, 0.0, 0.0],
        "max_flood_level_c": [8.0, 8.0, 0.0, 0.0],
        "max_flood_level_d": [3.0, 3.0, 0.0, 0.0],
    })


def test_flooded_substations_excludes_never_flooded():
    input1 = _toy_input1()
    filter_col = ["max_flood_level_a", "max_flood_level_b", "max_flood_level_c", "max_flood_level_d"]
    assert flooded_substations(input1, filter_col) == {10}


def test_decorrelated_preserves_marginals_and_zeros_unflooded():
    input1 = _toy_input1()
    filter_col = ["max_flood_level_a", "max_flood_level_b", "max_flood_level_c", "max_flood_level_d"]
    out = build_decorrelated_flood_df(input1, filter_col, seed=1)
    assert set(out.columns) == set(filter_col)
    # substation 20 stays all zero
    assert (out.loc[input1["SubNum"] == 20] == 0).all().all()
    # substation 10's multiset of values is unchanged (some permutation of {5,0,8,3})
    sub10 = out.loc[input1["SubNum"] == 10].iloc[0]
    assert sorted(sub10.values) == [0.0, 3.0, 5.0, 8.0]


def test_decorrelated_shares_value_across_buses_in_same_substation():
    input1 = _toy_input1()
    filter_col = ["max_flood_level_a", "max_flood_level_b", "max_flood_level_c", "max_flood_level_d"]
    out = build_decorrelated_flood_df(input1, filter_col, seed=7)
    sub10_rows = out.loc[input1["SubNum"] == 10]
    assert (sub10_rows.iloc[0] == sub10_rows.iloc[1]).all()


def test_validate_decorrelation_reports_pass():
    input1 = _toy_input1()
    filter_col = ["max_flood_level_a", "max_flood_level_b", "max_flood_level_c", "max_flood_level_d"]
    out = build_decorrelated_flood_df(input1, filter_col, seed=3)
    report = validate_decorrelation(input1, out, filter_col)
    assert report["marginals_preserved"] is True
    assert report["same_flooded_set"] is True
    assert report["shared_height_invariant"] is True


if __name__ == "__main__":
    test_flooded_substations_excludes_never_flooded()
    test_decorrelated_preserves_marginals_and_zeros_unflooded()
    test_decorrelated_shares_value_across_buses_in_same_substation()
    test_validate_decorrelation_reports_pass()
    print("All decorrelate.py tests passed.")
