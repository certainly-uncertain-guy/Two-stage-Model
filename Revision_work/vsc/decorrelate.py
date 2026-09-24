import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def flooded_substations(input1: pd.DataFrame, filter_col: list) -> set:
    sub_max = input1.groupby("SubNum")[filter_col].max().max(axis=1)
    return set(sub_max[sub_max > 0].index)


def build_decorrelated_flood_df(input1: pd.DataFrame, filter_col: list, seed: int) -> pd.DataFrame:
    """Independently permutes each flooded substation's scenario-to-height mapping.

    Substations outside I_f are left at zero. Every bus row belonging to the
    same SubNum receives the identical permuted value, matching the shared
    per-substation flood height the model constraints assume.
    """
    rng = np.random.default_rng(seed)
    i_f = flooded_substations(input1, filter_col)

    sub_values = input1.groupby("SubNum")[filter_col].first()  # one row per substation
    permuted = sub_values.copy()
    n_scen = len(filter_col)
    for sub in sub_values.index:
        if sub in i_f:
            perm = rng.permutation(n_scen)
            permuted.loc[sub, filter_col] = sub_values.loc[sub, filter_col].values[perm]
        else:
            permuted.loc[sub, filter_col] = 0.0

    out = input1[["SubNum"]].merge(permuted, left_on="SubNum", right_index=True, how="left")
    out.index = input1.index
    return out[filter_col]


def _mean_pairwise_spearman(flood_by_sub: pd.DataFrame) -> float:
    """flood_by_sub: rows = substations in I_f, columns = scenarios."""
    subs = flood_by_sub.index.tolist()
    corrs = []
    for a in range(len(subs)):
        for b in range(a + 1, len(subs)):
            va, vb = flood_by_sub.loc[subs[a]], flood_by_sub.loc[subs[b]]
            if va.nunique() <= 1 or vb.nunique() <= 1:
                continue
            rho, _ = spearmanr(va, vb)
            if not np.isnan(rho):
                corrs.append(rho)
    return float(np.mean(corrs)) if corrs else float("nan")


def validate_decorrelation(input1: pd.DataFrame, decorrelated: pd.DataFrame, filter_col: list) -> dict:
    i_f = flooded_substations(input1, filter_col)

    orig_by_sub = input1.groupby("SubNum")[filter_col].first()
    dec_by_sub = input1[["SubNum"]].join(decorrelated).groupby("SubNum")[filter_col].first()

    # 1. Marginals preserved (sorted per-substation vector unchanged)
    marginals_preserved = all(
        sorted(orig_by_sub.loc[s].values) == sorted(dec_by_sub.loc[s].values)
        for s in orig_by_sub.index
    )

    # 2. Same flooded set
    dec_input1 = input1[["SubNum"]].join(decorrelated)
    same_flooded_set = flooded_substations(dec_input1, filter_col) == i_f

    # 3. Correlation destroyed
    orig_corr = _mean_pairwise_spearman(orig_by_sub.loc[list(i_f)])
    dec_corr = _mean_pairwise_spearman(dec_by_sub.loc[list(i_f)])

    # 4. Simultaneous failures
    orig_counts = (orig_by_sub.loc[list(i_f)] > 0).sum(axis=0)
    dec_counts = (dec_by_sub.loc[list(i_f)] > 0).sum(axis=0)

    # 5. Shared-height invariant (every bus row in a substation matches every other)
    check_df = input1[["SubNum"]].join(decorrelated)
    shared_height_invariant = bool(
        check_df.groupby("SubNum")[filter_col].nunique().le(1).all().all()
    )

    return {
        "marginals_preserved": bool(marginals_preserved),
        "same_flooded_set": bool(same_flooded_set),
        "shared_height_invariant": shared_height_invariant,
        "orig_mean_spearman": orig_corr,
        "decorrelated_mean_spearman": dec_corr,
        "orig_simultaneous_failures_mean": float(orig_counts.mean()),
        "orig_simultaneous_failures_std": float(orig_counts.std()),
        "orig_simultaneous_failures_max": float(orig_counts.max()),
        "decorrelated_simultaneous_failures_mean": float(dec_counts.mean()),
        "decorrelated_simultaneous_failures_std": float(dec_counts.std()),
        "decorrelated_simultaneous_failures_max": float(dec_counts.max()),
    }
