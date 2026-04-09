import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import traceback
import os

from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import (
    safe_builtins,
    safer_getattr,                  # ✅ safer than raw getattr
    guarded_iter_unpack_sequence,
    guarded_unpack_sequence
)
from RestrictedPython.Eval import default_guarded_getitem  # ✅ the key fix

CHART_PATH = "output_chart.png"


def _safe_import(name, *args, **kwargs):
    """Only allow whitelisted imports inside LLM-generated code."""
    allowed = {"pandas", "matplotlib", "matplotlib.pyplot", "seaborn", "math", "statistics"}
    if name in allowed:
        return __import__(name, *args, **kwargs)
    raise ImportError(f"Import of '{name}' is not allowed in sandboxed execution.")


def build_restricted_globals(df: pd.DataFrame) -> dict:
    """Build a safe execution environment."""
    restricted_builtins = safe_builtins.copy()
    restricted_builtins["__import__"] = _safe_import

    glb = safe_globals.copy()
    glb["__builtins__"] = restricted_builtins

    # ✅ THE FIX — all 6 keys RestrictedPython needs for pandas operations
    glb["_getitem_"] = default_guarded_getitem   # df['Sales'], dict['key']
    glb["_getattr_"] = safer_getattr             # df.sum(), df.groupby()
    glb["_getiter_"] = iter                      # for loops
    glb["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence  # tuple unpacking
    glb["_unpack_sequence_"] = guarded_unpack_sequence            # sequence unpacking
    glb["_write_"] = lambda x: x                # result = ..., variable assignment
    glb["print"] = print 

    # Inject allowed tools
    glb["df"] = df
    glb["pd"] = pd
    glb["plt"] = plt
    glb["sns"] = sns

    return glb


def execute_code(code: str, df: pd.DataFrame):
    """
    Execute LLM-generated code inside a RestrictedPython sandbox.
    Returns: (result, chart_path, error)
    """
    if os.path.exists(CHART_PATH):
        os.remove(CHART_PATH)

    result = None
    chart_path = None
    error = None

    try:
        # Step 1: Compile with RestrictedPython
        byte_code = compile_restricted(code, filename="<llm_code>", mode="exec")

        if byte_code is None:
            raise ValueError("Code compilation failed — RestrictedPython rejected the code.")

        # Step 2: Build safe globals
        glb = build_restricted_globals(df)
        local_vars = {}

        # Step 3: Execute in sandbox
        exec(byte_code, glb, local_vars)

        # Step 4: Extract result
        if "result" in local_vars:
            result = local_vars["result"]
            if isinstance(result, pd.DataFrame):
                result = result.to_dict(orient="records")
            elif isinstance(result, pd.Series):
                result = result.to_dict()
            else:
                result = str(result)

        # Step 5: Check for chart
        if os.path.exists(CHART_PATH):
            chart_path = CHART_PATH

    except SyntaxError as e:
        error = f"Syntax error in generated code: {str(e)}"
    except ImportError as e:
        error = f"Blocked import attempt: {str(e)}"
    except Exception:
        error = traceback.format_exc()

    return result, chart_path, error