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
import uuid
from datetime import datetime

from agent import generate_code, generate_code_multi, fix_code, generate_summary, explain_error
from executor import execute_code, execute_code_multi
from mlflow_logger import log_query
from database import init_db, SessionLocal, QueryHistory, Favourite, DatasetMeta
from cache import (
    cache_dataframe, get_cached_dataframe, invalidate_cache,
    cache_schema, get_cached_schema,
    cache_summary, get_cached_summary
)

app = FastAPI(title="Data Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_RETRIES = 3
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploaded_datasets")
CHART_PATH = os.getenv("CHART_PATH", "output_chart.png")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CHART_PATH) if os.path.dirname(CHART_PATH) else ".", exist_ok=True)


# --- Startup ---

@app.on_event("startup")
def startup():
    init_db()


# --- Helpers ---

def sanitize_for_json(obj):
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


def generate_session_id(filename: str, content: bytes) -> str:
    file_hash = hashlib.md5(content).hexdigest()[:8]
    clean_name = filename.replace(".csv", "").replace(" ", "_")
    return f"{clean_name}_{file_hash}"


def load_dataframe(session_id: str) -> pd.DataFrame | None:
    # 1. Redis cache
    df = get_cached_dataframe(session_id)
    if df is not None:
        return df
    # 2. Disk fallback
    path = get_dataset_path(session_id)
    if os.path.exists(path):
        df = pd.read_csv(path)
        cache_dataframe(session_id, df)
        return df
    return None


def get_schema(session_id: str, df: pd.DataFrame) -> str:
    schema = get_cached_schema(session_id)
    if schema is None:
        schema = str(df.dtypes) + f"\n\nSample:\n{df.head(3).to_string()}"
        cache_schema(session_id, schema)
    return schema


# --- SQLite: History ---

def load_query_history(session_id: str) -> list:
    db = SessionLocal()
    try:
        rows = db.query(QueryHistory)\
                 .filter(QueryHistory.session_id == session_id)\
                 .order_by(QueryHistory.timestamp)\
                 .all()
        return [{"question": r.question, "code": r.code} for r in rows]
    finally:
        db.close()


def save_query_history(session_id: str, question: str, code: str):
    db = SessionLocal()
    try:
        db.add(QueryHistory(
            id=str(uuid.uuid4()),
            session_id=session_id,
            question=question,
            code=code
        ))
        db.commit()
    finally:
        db.close()


def clear_query_history(session_id: str):
    db = SessionLocal()
    try:
        db.query(QueryHistory)\
          .filter(QueryHistory.session_id == session_id)\
          .delete()
        db.commit()
    finally:
        db.close()


# --- SQLite: Favourites ---

def load_favourites(session_id: str) -> list:
    db = SessionLocal()
    try:
        rows = db.query(Favourite)\
                 .filter(Favourite.session_id == session_id)\
                 .order_by(Favourite.saved_at)\
                 .all()
        return [{"question": r.question, "code": r.code} for r in rows]
    finally:
        db.close()


def save_favourite(session_id: str, question: str, code: str) -> bool:
    db = SessionLocal()
    try:
        exists = db.query(Favourite)\
                   .filter(
                       Favourite.session_id == session_id,
                       Favourite.question == question
                   ).first()
        if exists:
            return False
        db.add(Favourite(
            id=str(uuid.uuid4()),
            session_id=session_id,
            question=question,
            code=code
        ))
        db.commit()
        return True
    finally:
        db.close()


def remove_favourite(session_id: str, question: str):
    db = SessionLocal()
    try:
        db.query(Favourite)\
          .filter(
              Favourite.session_id == session_id,
              Favourite.question == question
          ).delete()
        db.commit()
    finally:
        db.close()


# --- SQLite: Dataset Meta ---

def save_dataset_meta(session_id: str, filename: str, rows: int, columns: list, size_kb: float):
    db = SessionLocal()
    try:
        exists = db.query(DatasetMeta)\
                   .filter(DatasetMeta.session_id == session_id)\
                   .first()
        if not exists:
            db.add(DatasetMeta(
                session_id=session_id,
                filename=filename,
                rows=rows,
                columns_json=json.dumps(columns),
                size_kb=str(size_kb)
            ))
            db.commit()
    finally:
        db.close()


def list_datasets_from_db() -> list:
    db = SessionLocal()
    try:
        rows = db.query(DatasetMeta)\
                 .order_by(DatasetMeta.uploaded_at.desc())\
                 .all()
        return [
            {
                "session_id": r.session_id,
                "filename": r.filename,
                "rows": r.rows,
                "columns": json.loads(r.columns_json),
                "size_kb": r.size_kb,
                "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else ""
            }
            for r in rows
        ]
    finally:
        db.close()


def delete_dataset_meta(session_id: str):
    db = SessionLocal()
    try:
        db.query(DatasetMeta).filter(DatasetMeta.session_id == session_id).delete()
        db.query(QueryHistory).filter(QueryHistory.session_id == session_id).delete()
        db.query(Favourite).filter(Favourite.session_id == session_id).delete()
        db.commit()
    finally:
        db.close()


# --- Routes ---

@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
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

    # Save meta to SQLite
    save_dataset_meta(
        session_id=session_id,
        filename=file.filename,
        rows=df.shape[0],
        columns=list(df.columns),
        size_kb=round(os.path.getsize(path) / 1024, 2)
    )

    # Pre-warm Redis
    cache_dataframe(session_id, df)

    preview = sanitize_for_json(df.head(5).to_dict(orient="records"))
    return {
        "session_id": session_id,
        "columns": list(df.columns),
        "shape": df.shape,
        "preview": preview
    }


@app.post("/load")
async def load_dataset(session_id: str = Form(...)):
    df = load_dataframe(session_id)
    if df is None:
        return JSONResponse(status_code=404, content={"error": "Dataset not found."})

    # Check summary cache first
    summary = get_cached_summary(session_id)
    if summary is None:
        schema = get_schema(session_id, df)
        summary = generate_summary(schema)
        cache_summary(session_id, summary)

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

    schema = get_schema(session_id, df)
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

    log_query(
        question=question,
        generated_code=code,
        success=(error is None),
        error=error,
        attempts=attempts
    )

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

    code, chart_type = generate_code_multi(
        schemas=schemas,
        question=question,
        columns=all_columns
    )

    result, chart_path, error = execute_code_multi(code, dataframes)

    attempts = 1
    while error and attempts < MAX_RETRIES:
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
        "chart_type": chart_type,
        "attempts": attempts
    })


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
    clear_query_history(session_id)
    return {"message": "History cleared."}


@app.get("/datasets")
def list_datasets():
    return list_datasets_from_db()


@app.delete("/datasets/{session_id}")
def delete_dataset(session_id: str):
    path = get_dataset_path(session_id)
    if os.path.exists(path):
        os.remove(path)
    invalidate_cache(session_id)
    delete_dataset_meta(session_id)
    return {"message": f"Dataset '{session_id}' deleted."}


@app.post("/export/csv")
async def export_csv(session_id: str = Form(...), question: str = Form(...)):
    df = load_dataframe(session_id)
    if df is None:
        return JSONResponse(status_code=404, content={"error": "Dataset not found."})
    schema = get_schema(session_id, df)
    history = load_query_history(session_id)
    code, _ = await generate_code(
        schema=schema,
        question=question,
        columns=list(df.columns),
        history=history
    )
    result, _, error = execute_code(code, df.copy())
    if error or not result:
        return JSONResponse(status_code=500, content={"error": "Could not generate export."})
    result_df = pd.DataFrame(result) if isinstance(result, list) else pd.DataFrame([result])
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    result_df.to_csv(tmp.name, index=False)
    return FileResponse(tmp.name, media_type="text/csv", filename="result.csv")


@app.get("/chart")
def get_chart():
    return FileResponse(CHART_PATH, media_type="image/png")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "redis": REDIS_AVAILABLE if True else "fallback"
    }




# import for health check
try:
    from cache import REDIS_AVAILABLE
except:
    REDIS_AVAILABLE = False