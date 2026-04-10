import redis
import pickle
import pandas as pd
import os
import json

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
TTL_SECONDS = 60 * 60 * 2  # 2 hours

_memory_cache: dict = {}

try:
    r = redis.from_url(REDIS_URL, decode_responses=False)
    r.ping()
    REDIS_AVAILABLE = True
    print("[Cache] Redis connected ✅")
except Exception as e:
    REDIS_AVAILABLE = False
    print(f"[Cache] Redis unavailable, using memory fallback. Reason: {e}")


def cache_dataframe(session_id: str, df: pd.DataFrame):
    key = f"df:{session_id}"
    if REDIS_AVAILABLE:
        try:
            r.setex(key, TTL_SECONDS, pickle.dumps(df))
            print(f"[Cache] DataFrame cached: {session_id}")
            return
        except Exception as e:
            print(f"[Cache] Redis write failed: {e}")
    _memory_cache[key] = df


def get_cached_dataframe(session_id: str) -> pd.DataFrame | None:
    key = f"df:{session_id}"
    if REDIS_AVAILABLE:
        try:
            data = r.get(key)
            if data:
                print(f"[Cache] Redis hit (df): {session_id}")
                return pickle.loads(data)
        except Exception as e:
            print(f"[Cache] Redis read failed: {e}")
    return _memory_cache.get(key)


def invalidate_cache(session_id: str):
    if REDIS_AVAILABLE:
        try:
            r.delete(f"df:{session_id}")
            r.delete(f"schema:{session_id}")
            r.delete(f"summary:{session_id}")
        except Exception as e:
            print(f"[Cache] Redis delete failed: {e}")
    for prefix in ["df", "schema", "summary"]:
        _memory_cache.pop(f"{prefix}:{session_id}", None)


def cache_schema(session_id: str, schema: str):
    key = f"schema:{session_id}"
    if REDIS_AVAILABLE:
        try:
            r.setex(key, TTL_SECONDS, schema.encode())
            return
        except Exception as e:
            print(f"[Cache] Schema write failed: {e}")
    _memory_cache[key] = schema


def get_cached_schema(session_id: str) -> str | None:
    key = f"schema:{session_id}"
    if REDIS_AVAILABLE:
        try:
            data = r.get(key)
            if data:
                return data.decode()
        except Exception as e:
            print(f"[Cache] Schema read failed: {e}")
    return _memory_cache.get(key)


def cache_summary(session_id: str, summary: dict):
    key = f"summary:{session_id}"
    if REDIS_AVAILABLE:
        try:
            r.setex(key, TTL_SECONDS, json.dumps(summary).encode())
            return
        except Exception as e:
            print(f"[Cache] Summary write failed: {e}")
    _memory_cache[key] = summary


def get_cached_summary(session_id: str) -> dict | None:
    key = f"summary:{session_id}"
    if REDIS_AVAILABLE:
        try:
            data = r.get(key)
            if data:
                print(f"[Cache] Redis hit (summary): {session_id}")
                return json.loads(data.decode())
        except Exception as e:
            print(f"[Cache] Summary read failed: {e}")
    return _memory_cache.get(key)