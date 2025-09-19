# apps/api/database.py
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 🚫 SQLAlchemy 로그 전부 차단
logging.getLogger("sqlalchemy").setLevel(logging.CRITICAL)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meetings.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    echo=False,              # 반드시 False (환경변수로 덮어쓰지 않게!)
    pool_pre_ping=True,
    future=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()
