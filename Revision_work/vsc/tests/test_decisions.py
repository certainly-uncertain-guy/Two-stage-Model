import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from decisions import jaccard_index, mean_abs_height_diff, budget_allocation, selection_frequency


def test_jaccard_index_partial_overlap():
    x_so = {1: 3, 2: 0, 3: 5}   # selected: {1, 3}
    x_ind = {1: 2, 2: 4, 3: 0}  # selected: {1, 2}
    # intersection {1}, union {1,2,3} -> 1/3
    assert abs(jaccard_index(x_so, x_ind) - 1 / 3) < 1e-9


def test_jaccard_index_identical_sets():
    x_so = {1: 3, 2: 0}
    x_ind = {1: 5, 2: 0}
    assert jaccard_index(x_so, x_ind) == 1.0


def test_mean_abs_height_diff_only_over_common_selection():
    x_so = {1: 3, 2: 0, 3: 5}
    x_ind = {1: 5, 2: 4, 3: 0}
    # only substation 1 selected by both: |3-5| = 2
    assert mean_abs_height_diff(x_so, x_ind) == 2.0


def test_budget_allocation():
    x = {1: 3, 2: 0, 3: 5, 4: 0}
    out = budget_allocation(x)
    assert out["n_hardened"] == 2
    assert out["mean_height"] == 4.0


def test_selection_frequency_across_replications():
    x_ind_by_rep = {
        1: {10: 2, 20: 0},
        2: {10: 0, 20: 3},
        3: {10: 1, 20: 0},
    }
    freq = selection_frequency(x_ind_by_rep)
    assert freq[10] == 2 / 3
    assert freq[20] == 1 / 3


if __name__ == "__main__":
    test_jaccard_index_partial_overlap()
    test_jaccard_index_identical_sets()
    test_mean_abs_height_diff_only_over_common_selection()
    test_budget_allocation()
    test_selection_frequency_across_replications()
    print("All decisions.py tests passed.")
