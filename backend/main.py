from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import os
import hashlib

from agent import generate_code, fix_code
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

# ✅ Persistent storage folder
UPLOAD_DIR = "uploaded_datasets"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Create folder if not exists


def get_dataset_path(session_id: str) -> str:
    """Get the file path for a session's CSV."""
    return os.path.join(UPLOAD_DIR, f"{session_id}.csv")


def load_dataframe(session_id: str) -> pd.DataFrame | None:
    """Load DataFrame from disk. Returns None if not found."""
    path = get_dataset_path(session_id)
    if os.path.exists(path):
        return pd.read_csv(path)
    return None


def generate_session_id(filename: str, content: bytes) -> str:
    """
    Generate a unique session ID based on filename + file content hash.
    Same file = same session ID, so re-uploads are idempotent.
    """
    file_hash = hashlib.md5(content).hexdigest()[:8]
    clean_name = filename.replace(".csv", "").replace(" ", "_")
    return f"{clean_name}_{file_hash}"


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    contents = await file.read()

    # Generate stable session ID from file content
    session_id = generate_session_id(file.filename, contents)
    path = get_dataset_path(session_id)

    # ✅ Only save if not already on disk (avoid re-processing same file)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(contents)
        print(f"[Upload] Saved new dataset: {path}")
    else:
        print(f"[Upload] Dataset already exists, reusing: {path}")

    df = pd.read_csv(io.StringIO(contents.decode("utf-8")))

    return {
        "session_id": session_id,
        "columns": list(df.columns),
        "shape": df.shape,
        "preview": df.head(5).to_dict(orient="records"),
        "cached": os.path.exists(path)  # Tell frontend if it was already cached
    }


@app.post("/query")
async def query(session_id: str = Form(...), question: str = Form(...)):
    # ✅ Load from disk instead of memory
    df = load_dataframe(session_id)

    if df is None:
        return JSONResponse(status_code=404, content={
            "error": "Dataset not found. Please re-upload your CSV."
        })

    schema = str(df.dtypes) + f"\n\nSample:\n{df.head(3).to_string()}"

    code = generate_code(schema=schema, question=question)
    result, chart_path, error = execute_code(code, df.copy())

    attempts = 1

    while error and attempts < MAX_RETRIES:
        print(f"[Retry {attempts}] Fixing code...")
        code = fix_code(schema=schema, question=question, bad_code=code, error=error)
        result, chart_path, error = execute_code(code, df.copy())
        attempts += 1

    log_query(question=question, generated_code=code, success=(error is None), error=error, attempts=attempts)

    if error:
        return JSONResponse(status_code=500, content={
            "error": f"Failed after {attempts} attempts.\n\n{error}",
            "generated_code": code
        })

    return {
        "question": question,
        "generated_code": code,
        "result": result,
        "has_chart": chart_path is not None,
        "attempts": attempts
    }


@app.get("/datasets")
def list_datasets():
    """List all datasets currently stored on disk."""
    files = os.listdir(UPLOAD_DIR)
    datasets = []
    for f in files:
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
    """Delete a stored dataset."""
    path = get_dataset_path(session_id)
    if os.path.exists(path):
        os.remove(path)
        return {"message": f"Dataset '{session_id}' deleted."}
    return JSONResponse(status_code=404, content={"error": "Dataset not found."})


@app.get("/chart")
def get_chart():
    return FileResponse("output_chart.png", media_type="image/png")


@app.get("/health")
def health():
    return {"status": "ok"}