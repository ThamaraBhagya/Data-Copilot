from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os
import json
import uuid

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./copilot.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class QueryHistory(Base):
    __tablename__ = "query_history"
    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    question = Column(Text)
    code = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Favourite(Base):
    __tablename__ = "favourites"
    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    question = Column(Text)
    code = Column(Text)
    saved_at = Column(DateTime, default=datetime.utcnow)


class DatasetMeta(Base):
    __tablename__ = "datasets"
    session_id = Column(String, primary_key=True)
    filename = Column(String)
    rows = Column(Integer)
    columns_json = Column(Text)
    size_kb = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
    print("[DB] SQLite initialized ")




# --- Dataset Meta Helpers ---
def save_dataset_meta(session_id: str, filename: str, rows: int, columns: list, size_kb: float):
    db = SessionLocal()
    try:
        exists = db.query(DatasetMeta).filter(DatasetMeta.session_id == session_id).first()
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
        rows = db.query(DatasetMeta).order_by(DatasetMeta.uploaded_at.desc()).all()
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


# --- Query History Helpers ---
def load_query_history(session_id: str) -> list:
    db = SessionLocal()
    try:
        rows = db.query(QueryHistory).filter(QueryHistory.session_id == session_id).order_by(QueryHistory.timestamp).all()
        return [{"question": r.question, "code": r.code} for r in rows]
    finally:
        db.close()

def save_query_history(session_id: str, question: str, code: str):
    db = SessionLocal()
    try:
        db.add(QueryHistory(id=str(uuid.uuid4()), session_id=session_id, question=question, code=code))
        db.commit()
    finally:
        db.close()

def clear_query_history(session_id: str):
    db = SessionLocal()
    try:
        db.query(QueryHistory).filter(QueryHistory.session_id == session_id).delete()
        db.commit()
    finally:
        db.close()


# --- Favourites Helpers ---
def load_favourites(session_id: str) -> list:
    db = SessionLocal()
    try:
        rows = db.query(Favourite).filter(Favourite.session_id == session_id).order_by(Favourite.saved_at).all()
        return [{"question": r.question, "code": r.code} for r in rows]
    finally:
        db.close()

def save_favourite(session_id: str, question: str, code: str) -> bool:
    db = SessionLocal()
    try:
        exists = db.query(Favourite).filter(Favourite.session_id == session_id, Favourite.question == question).first()
        if exists:
            return False
        db.add(Favourite(id=str(uuid.uuid4()), session_id=session_id, question=question, code=code))
        db.commit()
        return True
    finally:
        db.close()

def remove_favourite(session_id: str, question: str):
    db = SessionLocal()
    try:
        db.query(Favourite).filter(Favourite.session_id == session_id, Favourite.question == question).delete()
        db.commit()
    finally:
        db.close()