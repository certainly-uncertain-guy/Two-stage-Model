from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR_16 = REPO_ROOT / "fixed_reduced_grid" / "16_Scenario"
SM16_OUTPUT_DIR = REPO_ROOT / "output" / "sm_16"
WAIT_AND_SEE_JSON = REPO_ROOT / "output_analysis" / "wait_and_see_dict.json"
VSC_RESULTS_DIR = REPO_ROOT / "vsc_results"

VSC_RESULTS_DIR.mkdir(exist_ok=True)


def input_dir_str(path: Path = INPUT_DIR_16) -> str:
    """utils.prepare_input does `path_str + "Final_Input1.csv"`, so it needs a trailing slash."""
    s = str(path)
    return s if s.endswith("/") else s + "/"
