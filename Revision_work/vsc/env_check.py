def check_environment():
    try:
        import gurobipy as gp
    except ImportError as e:
        raise RuntimeError(
            "gurobipy is not importable in this Python environment. "
            "Neither the system python3 (/usr/bin/python3) nor the active "
            "conda env (/opt/miniconda3) has gurobipy or pyomo installed as of "
            "this plan's authoring. Install gurobipy (`pip install gurobipy` or "
            "`conda install -c gurobi gurobi`) and ensure a valid Gurobi license "
            "is available before running any part of this experiment."
        ) from e
    try:
        m = gp.Model()
        m.dispose()
    except gp.GurobiError as e:
        raise RuntimeError(
            f"gurobipy imported but could not create a model (license problem?): {e}"
        ) from e
