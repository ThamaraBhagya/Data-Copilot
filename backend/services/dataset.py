import os
import hashlib
import math
import pandas as pd
import io
from core.config import UPLOAD_DIR
from cache import get_cached_dataframe, cache_dataframe, get_cached_schema, cache_schema

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