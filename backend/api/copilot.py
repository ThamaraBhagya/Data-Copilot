from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse, FileResponse
import pandas as pd
import tempfile
from core.config import MAX_RETRIES, CHART_PATH
from services.dataset import load_dataframe, get_schema, sanitize_for_json
from agent import generate_code, generate_code_multi, fix_code, explain_error
from executor import execute_code, execute_code_multi
from mlflow_logger import log_query
from database import (
    load_query_history, save_query_history, clear_query_history,
    load_favourites, save_favourite, remove_favourite
)

router = APIRouter(tags=["Copilot"])

@router.post("/query")
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

@router.post("/query/multi")
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

@router.post("/favourites/{session_id}")
async def add_favourite(session_id: str, question: str = Form(...), code: str = Form(...)):
    added = save_favourite(session_id, question, code)
    if added:
        return {"message": "Added to favourites."}
    return JSONResponse(status_code=409, content={"error": "Already in favourites."})

@router.get("/favourites/{session_id}")
def get_favourites(session_id: str):
    return load_favourites(session_id)

@router.delete("/favourites/{session_id}")
async def delete_favourite(session_id: str, question: str = Form(...)):
    remove_favourite(session_id, question)
    return {"message": "Removed from favourites."}

@router.get("/history/{session_id}")
def get_history(session_id: str):
    return load_query_history(session_id)

@router.delete("/history/{session_id}")
def clear_history(session_id: str):
    clear_query_history(session_id)
    return {"message": "History cleared."}

@router.post("/export/csv")
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

@router.get("/chart")
def get_chart():
    return FileResponse(CHART_PATH, media_type="image/png")