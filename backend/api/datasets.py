from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
import pandas as pd
import io
import os
from services.dataset import (
    generate_session_id, get_dataset_path, load_dataframe, get_schema, sanitize_for_json
)
from database import save_dataset_meta, list_datasets_from_db, delete_dataset_meta
from cache import cache_dataframe, get_cached_summary, cache_summary, invalidate_cache
from agent import generate_summary

router = APIRouter(tags=["Datasets"])

@router.post("/upload")
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

@router.post("/load")
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

@router.get("/datasets")
def list_datasets():
    return list_datasets_from_db()

@router.delete("/datasets/{session_id}")
def delete_dataset(session_id: str):
    path = get_dataset_path(session_id)
    if os.path.exists(path):
        os.remove(path)
    invalidate_cache(session_id)
    delete_dataset_meta(session_id)
    return {"message": f"Dataset '{session_id}' deleted."}