from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import os
import hashlib
import json
import tempfile
import math
from datetime import datetime

from agent import generate_code, generate_code_multi, fix_code, generate_summary, explain_error
from executor import execute_code
from mlflow_logger import log_query

app = FastAPI(title="Data Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_RETRIES = 3
UPLOAD_DIR = "uploaded_datasets"
HISTORY_DIR = "query_history"
FAVOURITES_DIR = "favourites"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(FAVOURITES_DIR, exist_ok=True)


# --- Helpers ---

def sanitize_for_json(obj):
    """Recursively replace nan/inf with None for JSON safety."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    return obj


def get_dataset_path(session_id: str) -> str:
    return os.path.join(UPLOAD_DIR, f"{session_id}.csv")


def get_history_path(session_id: str) -> str:
    return os.path.join(HISTORY_DIR, f"{session_id}.json")


def get_favourites_path(session_id: str) -> str:
    return os.path.join(FAVOURITES_DIR, f"{session_id}.json")


def load_dataframe(session_id: str) -> pd.DataFrame | None:
    path = get_dataset_path(session_id)
    if os.path.exists(path):
        return pd.read_csv(path)
    return None


def generate_session_id(filename: str, content: bytes) -> str:
    file_hash = hashlib.md5(content).hexdigest()[:8]
    clean_name = filename.replace(".csv", "").replace(" ", "_")
    return f"{clean_name}_{file_hash}"


def load_query_history(session_id: str) -> list:
    path = get_history_path(session_id)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def save_query_history(session_id: str, question: str, code: str):
    path = get_history_path(session_id)
    history = load_query_history(session_id)
    history.append({
        "question": question,
        "code": code,
        "timestamp": datetime.now().isoformat()
    })
    with open(path, "w") as f:
        json.dump(history, f)


def load_favourites(session_id: str) -> list:
    path = get_favourites_path(session_id)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def save_favourite(session_id: str, question: str, code: str):
    path = get_favourites_path(session_id)
    favs = load_favourites(session_id)
    # Avoid duplicates
    if any(f["question"] == question for f in favs):
        return False
    favs.append({
        "question": question,
        "code": code,
        "saved_at": datetime.now().isoformat()
    })
    with open(path, "w") as f:
        json.dump(favs, f)
    return True


def remove_favourite(session_id: str, question: str):
    path = get_favourites_path(session_id)
    favs = load_favourites(session_id)
    favs = [f for f in favs if f["question"] != question]
    with open(path, "w") as f:
        json.dump(favs, f)


# --- Routes ---

@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Save CSV to disk only. Does not auto-load."""
    contents = await file.read()
    session_id = generate_session_id(file.filename, contents)
    path = get_dataset_path(session_id)

    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(contents)
        print(f"[Upload] Saved: {path}")
    else:
        print(f"[Upload] Already exists: {path}")

    df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    preview = sanitize_for_json(df.head(5).to_dict(orient="records"))

    return {
        "session_id": session_id,
        "columns": list(df.columns),
        "shape": df.shape,
        "preview": preview
    }


@app.post("/load")
async def load_dataset(session_id: str = Form(...)):
    """Load a dataset and generate its summary."""
    df = load_dataframe(session_id)
    if df is None:
        return JSONResponse(status_code=404, content={"error": "Dataset not found."})

    schema = str(df.dtypes) + f"\n\nFirst 5 rows:\n{df.head(5).to_string()}"
    summary = generate_summary(schema)
    preview = sanitize_for_json(df.head(5).to_dict(orient="records"))

    return {
        "session_id": session_id,
        "columns": list(df.columns),
        "shape": df.shape,
        "preview": preview,
        "summary": summary
    }

@app.post("/query")
async def query(session_id: str = Form(...), question: str = Form(...)):
    df = load_dataframe(session_id)
    if df is None:
        return JSONResponse(status_code=404, content={"error": "Dataset not found."})

    # ✅ Use cached schema — avoids recomputing on every query
    from agent import get_schema
    schema = get_schema(df, session_id)
    history = load_query_history(session_id)
    columns = list(df.columns)

    code, chart_type = await generate_code(
        schema=schema,
        question=question,
        columns=columns,
        history=history
    )

    result, chart_path, error = execute_code(code, df.copy())

    attempts = 1
    while error and attempts < MAX_RETRIES:
        print(f"[Retry {attempts}] Fixing...")
        code = fix_code(schema=schema, question=question, bad_code=code, error=error)
        result, chart_path, error = execute_code(code, df.copy())
        attempts += 1

    if not error:
        save_query_history(session_id, question, code)

    log_query(question=question, generated_code=code, success=(error is None), error=error, attempts=attempts)

    if error:
        friendly = explain_error(question=question, error=error)
        return JSONResponse(status_code=500, content={
            "friendly_error": friendly,
            "technical_error": error,
            "generated_code": code
        })

    return sanitize_for_json({
        "question": question,
        "generated_code": code,
        "result": result,
        "has_chart": chart_path is not None,
        "chart_type": chart_type,
        "attempts": attempts
    })


@app.post("/query/multi")
async def query_multi(session_ids: str = Form(...), question: str = Form(...)):
    ids = [s.strip() for s in session_ids.split(",")]
    dataframes = {}
    schemas = ""
    all_columns = []

    for i, sid in enumerate(ids):
        df = load_dataframe(sid)
        if df is None:
            return JSONResponse(status_code=404, content={"error": f"Dataset '{sid}' not found."})
        var_name = f"df_{i+1}"
        dataframes[var_name] = df
        schemas += f"\n{var_name} → '{sid}'\nColumns:\n{str(df.dtypes)}\nSample:\n{df.head(2).to_string()}\n"
        all_columns.extend(list(df.columns))

    # ✅ generate_code_multi now returns (code, chart_type)
    code, chart_type = generate_code_multi(
        schemas=schemas,
        question=question,
        columns=all_columns
    )

    result, chart_path, error = execute_code_multi(code, dataframes)

    attempts = 1
    while error and attempts < MAX_RETRIES:
        print(f"[Multi Retry {attempts}]")
        code = fix_code(schema=schemas, question=question, bad_code=code, error=error)
        result, chart_path, error = execute_code_multi(code, dataframes)
        attempts += 1

    if error:
        friendly = explain_error(question=question, error=error)
        return JSONResponse(status_code=500, content={
            "friendly_error": friendly,
            "technical_error": error,
            "generated_code": code
        })

    return sanitize_for_json({
        "question": question,
        "generated_code": code,
        "result": result,
        "has_chart": chart_path is not None,
        "chart_type": chart_type,   # ✅ send to frontend
        "attempts": attempts
    })


# ✅ NEW: Favourites endpoints
@app.post("/favourites/{session_id}")
async def add_favourite(session_id: str, question: str = Form(...), code: str = Form(...)):
    added = save_favourite(session_id, question, code)
    if added:
        return {"message": "Added to favourites."}
    return JSONResponse(status_code=409, content={"error": "Already in favourites."})


@app.get("/favourites/{session_id}")
def get_favourites(session_id: str):
    return load_favourites(session_id)


@app.delete("/favourites/{session_id}")
async def delete_favourite(session_id: str, question: str = Form(...)):
    remove_favourite(session_id, question)
    return {"message": "Removed from favourites."}


@app.get("/history/{session_id}")
def get_history(session_id: str):
    return load_query_history(session_id)


@app.delete("/history/{session_id}")
def clear_history(session_id: str):
    path = get_history_path(session_id)
    if os.path.exists(path):
        os.remove(path)
    return {"message": "History cleared."}


@app.get("/datasets")
def list_datasets():
    datasets = []
    for f in os.listdir(UPLOAD_DIR):
        if not f.endswith(".csv"):
            continue
        path = os.path.join(UPLOAD_DIR, f)
        df = pd.read_csv(path)
        datasets.append({
            "session_id": f.replace(".csv", ""),
            "filename": f,
            "rows": df.shape[0],
            "columns": list(df.columns),
            "size_kb": round(os.path.getsize(path) / 1024, 2)
        })
    return datasets


@app.delete("/datasets/{session_id}")
def delete_dataset(session_id: str):
    path = get_dataset_path(session_id)
    if os.path.exists(path):
        os.remove(path)
        for p in [get_history_path(session_id), get_favourites_path(session_id)]:
            if os.path.exists(p):
                os.remove(p)
        return {"message": f"Dataset '{session_id}' deleted."}
    return JSONResponse(status_code=404, content={"error": "Dataset not found."})


@app.post("/export/csv")
async def export_csv(session_id: str = Form(...), question: str = Form(...)):
    df = load_dataframe(session_id)
    if df is None:
        return JSONResponse(status_code=404, content={"error": "Dataset not found."})
    schema = str(df.dtypes)
    history = load_query_history(session_id)
    code = generate_code(schema=schema, question=question, history=history)
    result, _, error = execute_code(code, df.copy())
    if error or not result:
        return JSONResponse(status_code=500, content={"error": "Could not generate export."})
    result_df = pd.DataFrame(result) if isinstance(result, list) else pd.DataFrame([result])
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    result_df.to_csv(tmp.name, index=False)
    return FileResponse(tmp.name, media_type="text/csv", filename="result.csv")


@app.get("/chart")
def get_chart():
    return FileResponse("output_chart.png", media_type="image/png")


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Multi-CSV executor helper ---
def execute_code_multi(code: str, dataframes: dict):
    """Execute code with multiple DataFrames injected."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
    import traceback

    CHART_PATH = "output_chart.png"
    if os.path.exists(CHART_PATH):
        os.remove(CHART_PATH)

    result = None
    chart_path = None
    error = None

    try:
        from RestrictedPython import compile_restricted
        from RestrictedPython.Guards import safe_builtins, safer_getattr, guarded_iter_unpack_sequence, guarded_unpack_sequence
        from RestrictedPython.Eval import default_guarded_getitem

        byte_code = compile_restricted(code, filename="<llm_multi>", mode="exec")

        glb = {
            "__builtins__": safe_builtins,
            "_getitem_": default_guarded_getitem,
            "_getattr_": safer_getattr,
            "_getiter_": iter,
            "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
            "_unpack_sequence_": guarded_unpack_sequence,
            "_write_": lambda x: x,
            "print": print,
            "pd": pd,
            "plt": plt,
            "sns": sns,
        }

        # ✅ Inject all DataFrames
        local_vars = {**dataframes}

        exec(byte_code, glb, local_vars)

        if "result" in local_vars:
            result = local_vars["result"]
            if isinstance(result, pd.DataFrame):
                result = result.to_dict(orient="records")
            elif isinstance(result, pd.Series):
                result = result.to_dict()
            else:
                result = str(result)

        if os.path.exists(CHART_PATH):
            chart_path = CHART_PATH

    except Exception:
        error = traceback.format_exc()

    return result, chart_path, error