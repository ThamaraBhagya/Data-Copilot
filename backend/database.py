from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

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
    print("[DB] SQLite initialized ✅")