# apps/api/database.py
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

logging.getLogger("sqlalchemy").setLevel(logging.CRITICAL)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meetings.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# ✅ FastAPI 의존성: 요청마다 세션 열고 닫기
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
