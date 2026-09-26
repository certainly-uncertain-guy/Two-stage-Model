"""sys.path wiring and paths for the slow-storm sensitivity experiment.

Spec: Revision_work/slow_storm_sensitivity_experiment.md. Reuses
Revision_work/certainty/common.py, which in turn puts Revision_work/vsc/ and the
repo root on sys.path. Module names here are prefixed (slow_*, storm_*) so they
never collide with vsc/ or certainty/ modules.
"""
import sys
from pathlib import Path

SLOW_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SLOW_DIR.parent / "certainty"))

from common import (CERTAINTY_RESULTS_DIR, REPO_ROOT, SCENARIO_PREFIX,  # noqa: E402,F401
                    SM16_OUTPUT_DIR, WAIT_AND_SEE_JSON, append_row, apply_solver_params,
                    flood_columns, read_rows, scenario_subset_input1, short_name)

RM16_OUTPUT_DIR = REPO_ROOT / "output" / "rm_16"
SLOW_RESULTS_DIR = REPO_ROOT / "slow_storm_results"
