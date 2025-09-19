# apps/api/routers/actions.py  (교체)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date as _date
from .. import database, models

router = APIRouter(prefix="/meetings")

# DB DI
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_meeting(db: Session, meeting_id: str) -> models.Meeting:
    m = db.get(models.Meeting, meeting_id)
    if not m:
        raise HTTPException(status_code=404, detail="UNKNOWN_MEETING")
    return m

# PATCH 바디 스키마 (UI 항목 전부: 프로젝트명 제외)
class TaskPatch(BaseModel):
    title: Optional[str] = None
    # owner_name: Optional[str] = None            # 단일 대표 담당자 → Task.assignee
    assignees: Optional[list[str]] = None       # 다중 작업자 → assignees_json
    watchers: Optional[list[str]] = None        # 관람자 → watchers_json
    note: Optional[str] = None

    start_date: Optional[str] = None            # "YYYY-MM-DD"
    end_date: Optional[str] = None
    completed_date: Optional[str] = None
    due_date: Optional[str] = None

    status: Optional[str] = None                # todo/in_progress/feedback/on_hold/canceled/done
    task_type: Optional[str] = None             # 일반/체크리스트/데이터 취합/투표
    priority: Optional[str] = None              # 낮음/보통/높음/긴급

    work_time: Optional[str | int] = None       # "1:30" 또는 90(분)

# ── helpers ───────────────────────────────────────────────────────────────

def _parse_date(s: str | None) -> _date | None:
    if not s:
        return None
    try:
        y, m, d = [int(x) for x in s.strip().split("-")]
        return _date(y, m, d)
    except Exception:
        raise HTTPException(status_code=400, detail="INVALID_DATE")

def parse_minutes(s: str | int | None) -> int:
    if s is None:
        return 0
    if isinstance(s, int):
        return max(0, s)
    ss = s.strip()
    if ":" in ss:  # "H:MM"
        h, m = ss.split(":")
        return max(0, int(h) * 60 + int(m))
    return max(0, int(ss))

def opt_str(maxlen: int):
    return lambda v: ((v or "").strip()[:maxlen]) or None

def req_str(maxlen: int):
    def f(v):
        val = (v or "").strip()
        if not val:
            raise HTTPException(status_code=400, detail="TITLE_REQUIRED")
        return val[:maxlen]
    return f

def list_of_str(v):
    if v is None:
        return None
    if not isinstance(v, list):
        raise HTTPException(status_code=400, detail="MUST_BE_LIST")
    out, seen = [], set()
    for x in v:
        s = str(x).strip()
        if s and s not in seen:
            out.append(s[:128]); seen.add(s)
    return out or None

def enum_conv(enum_cls, *, aliases: dict[str, str] | None = None, lower: bool = True):
    table = { (e.value.lower() if lower else e.value): e for e in enum_cls }
    if aliases:
        for k, v in aliases.items():
            table[k.lower() if lower else k] = table[v.lower() if lower else v]
    def convert(val):
        if val is None:
            return None
        key = str(val).strip()
        key = key.lower() if lower else key
        if key not in table:
            raise HTTPException(status_code=400, detail=f"INVALID_{enum_cls.__name__.upper()}")
        return table[key]
    return convert

# ── converters ────────────────────────────────────────────────────────────
status_from_str = enum_conv(models.TaskStatus, aliases={"cancelled": "canceled"}, lower=True)
type_from_str   = enum_conv(models.TaskType,  lower=False)  # "일반","체크리스트","데이터 취합","투표"
prio_from_str   = enum_conv(models.Priority,  lower=False)  # "낮음","보통","높음","긴급"

# ── PATCH 핸들러 ──────────────────────────────────────────────────────────
@router.patch("/{meeting_id}/actions/{action_id}")
def update_task(
    meeting_id: str,
    action_id: int,
    patch: TaskPatch,
    db: Session = Depends(get_db),
):
    require_meeting(db, meeting_id)

    t = (
        db.query(models.Task)
        .filter(models.Task.id == action_id, models.Task.meeting_id == meeting_id)
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail="ACTION_NOT_FOUND")

    data = patch.model_dump(exclude_unset=True)

    # 입력키 → (모델필드, 변환기)
    FIELD_SPECS = {
        "title":          ("title",          req_str(512)),
        #"owner_name":     ("assignee",       opt_str(128)),
        "assignees":      ("assignees_json", list_of_str),
        "watchers":       ("watchers_json",  list_of_str),
        "note":           ("note",           lambda v: (v or "")[:2000]),
        "start_date":     ("start_date",     _parse_date),
        "end_date":       ("end_date",       _parse_date),
        "completed_date": ("completed_date", _parse_date),
        "due_date":       ("due_date",       _parse_date),
        "work_time":      ("work_time_min",  parse_minutes),
        "status":         ("status",         status_from_str),
        "task_type":      ("task_type",      type_from_str),
        "priority":       ("priority",       prio_from_str),
    }

    for key, val in data.items():
        spec = FIELD_SPECS.get(key)
        if not spec:
            continue  # 알 수 없는 키 무시
        attr, conv = spec
        new_val = conv(val)
        if getattr(t, attr) != new_val:
            setattr(t, attr, new_val)

    db.commit()
    db.refresh(t)

    return {
        "id": t.id,
        "meeting_id": t.meeting_id,
        "title": t.title,
        "assignee": t.assignee,
        "assignees": t.assignees_json or [],
        "watchers": t.watchers_json or [],
        "note": t.note,
        "start_date": t.start_date.isoformat() if t.start_date else None,
        "end_date": t.end_date.isoformat() if t.end_date else None,
        "completed_date": t.completed_date.isoformat() if t.completed_date else None,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "work_time_min": t.work_time_min,
        "status": t.status.value,
        "status_label": t.status.label if hasattr(t.status, "label") else t.status.value,

        "task_type": t.task_type.value,
        "priority": t.priority.value if t.priority else None,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }
