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
    safer_getattr,
    guarded_iter_unpack_sequence,
    guarded_unpack_sequence
)
from RestrictedPython.Eval import default_guarded_getitem

CHART_PATH = os.getenv("CHART_PATH", "output_chart.png")


def _safe_import(name, *args, **kwargs):
    """Only allow whitelisted imports inside LLM-generated code."""
    allowed = {
        "pandas", "matplotlib", "matplotlib.pyplot",
        "seaborn", "math", "statistics"
    }
    if name in allowed:
        return __import__(name, *args, **kwargs)
    raise ImportError(f"Import of '{name}' is not allowed in sandboxed execution.")


def build_restricted_globals(dataframes: dict) -> dict:
    """
    Build a safe sandbox environment.
    Accepts a dict of DataFrames — works for both single and multi CSV.

    Single CSV:  build_restricted_globals({"df": df})
    Multi CSV:   build_restricted_globals({"df_1": df1, "df_2": df2})
    """
    restricted_builtins = safe_builtins.copy()
    restricted_builtins["__import__"] = _safe_import  # whitelisted imports only

    glb = safe_globals.copy()
    glb["__builtins__"] = restricted_builtins

    # All keys RestrictedPython needs for pandas operations
    glb["_getitem_"] = default_guarded_getitem          # df['col'], dict['key']
    glb["_getattr_"] = safer_getattr                    # df.sum(), df.groupby()
    glb["_getiter_"] = iter                             # for loops
    glb["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence  # k, v unpacking
    glb["_unpack_sequence_"] = guarded_unpack_sequence            # a, b = tuple
    glb["_write_"] = lambda x: x                        # result = ...
    glb["print"] = print                                # forgive accidental prints

    
    glb["pd"] = pd
    glb["plt"] = plt
    glb["sns"] = sns

    
    for name, df_obj in dataframes.items():
        glb[name] = df_obj

    return glb


def _extract_result(local_vars: dict):
    """Extract and serialize the result variable from executed code."""
    result = local_vars.get("result")
    if result is None:
        return None
    if isinstance(result, pd.DataFrame):
        return result.to_dict(orient="records")
    elif isinstance(result, pd.Series):
        return result.to_dict()
    else:
        return str(result)


def execute_code(code: str, df: pd.DataFrame):
    """
    Execute LLM code for a SINGLE CSV in sandbox.
    Returns: (result, chart_path, error)
    """
    if os.path.exists(CHART_PATH):
        os.remove(CHART_PATH)

    result = None
    chart_path = None
    error = None

    try:
        byte_code = compile_restricted(code, filename="<llm_code>", mode="exec")

        if byte_code is None:
            raise ValueError("RestrictedPython rejected the code at compile time.")

        
        glb = build_restricted_globals({"df": df})
        local_vars = {}

        exec(byte_code, glb, local_vars)

        result = _extract_result(local_vars)

        if os.path.exists(CHART_PATH):
            chart_path = CHART_PATH

    except SyntaxError as e:
        error = f"Syntax error in generated code: {str(e)}"
    except ImportError as e:
        error = f"Blocked import attempt: {str(e)}"
    except Exception:
        error = traceback.format_exc()

    return result, chart_path, error


def execute_code_multi(code: str, dataframes: dict):
    """
    Execute LLM code for MULTIPLE CSVs in sandbox.
    dataframes = {"df_1": df1, "df_2": df2, ...}
    Returns: (result, chart_path, error)
    """
    if os.path.exists(CHART_PATH):
        os.remove(CHART_PATH)

    result = None
    chart_path = None
    error = None

    try:
        byte_code = compile_restricted(code, filename="<llm_multi>", mode="exec")

        if byte_code is None:
            raise ValueError("RestrictedPython rejected the code at compile time.")

        
        glb = build_restricted_globals(dataframes)
        local_vars = {}

        exec(byte_code, glb, local_vars)

        result = _extract_result(local_vars)

        if os.path.exists(CHART_PATH):
            chart_path = CHART_PATH

    except SyntaxError as e:
        error = f"Syntax error in generated code: {str(e)}"
    except ImportError as e:
        error = f"Blocked import attempt: {str(e)}"
    except Exception:
        error = traceback.format_exc()

    return result, chart_path, error