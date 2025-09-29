from dotenv import load_dotenv
load_dotenv()  # .env 로드 (최상단)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine

from . import models 
models.Base.metadata.create_all(bind=engine)

# 라우터 import (모델 import보다 늦어도 OK)
from .routers import meetings, actions, handoff, checklist
from .routers.vote import router as vote_router



FRONT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://15.164.234.96:5173",  # ← EC2 IP + 포트(필수)
    "http://15.164.234.96:5174",  # ← 가끔 5174로 뜬 경우 대비(옵션)
    "http://ec2-15-164-234-96.ap-northeast-2.compute.amazonaws.com",  # ← 추가
]

# apps/api/main.py
import logging

# (선택) 루트는 WARNING으로 유지
logging.basicConfig(level=logging.WARNING)

# 우리 앱 로거만 INFO로 살림
app_logger = logging.getLogger("app.meetings")
app_logger.setLevel(logging.INFO)
# 핸들러가 없으면 하나 달아줌 (중복 방지)
if not app_logger.handlers:
    h = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    h.setFormatter(fmt)
    app_logger.addHandler(h)

# SQLAlchemy는 전부 묵음
for name in ("sqlalchemy", "sqlalchemy.engine", "sqlalchemy.pool"):
    lg = logging.getLogger(name)
    lg.setLevel(logging.CRITICAL)
    lg.propagate = False
    lg.handlers.clear()

# uvicorn/스타렛도 묵음(원하면 유지)
logging.getLogger("uvicorn").setLevel(logging.CRITICAL)
logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL)
logging.getLogger("uvicorn.access").setLevel(logging.CRITICAL)
logging.getLogger("starlette").setLevel(logging.CRITICAL)


app = FastAPI(title="Meeting Assistant API")

# 위에 이미 FRONT_ORIGINS 정의해두셨죠
# FRONT_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONT_ORIGINS,
    allow_credentials=True,   # 쿠키/인증 안 쓸 거면 False로 내려도 됨
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # 테이블 생성
    Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "Meeting Assistant API"}

@app.get("/health")
def health():
    return {"ok": True}

# 라우터 마운트
app.include_router(meetings.router, tags=["meetings"])
app.include_router(actions.router,  tags=["actions"])
app.include_router(handoff.router,  tags=["handoff"])
app.include_router(vote_router,  tags=["vote"])
app.include_router(checklist.router, tags=["checklist"])