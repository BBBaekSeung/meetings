# apps/api/routers/actions.py  (교체)

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date as _date, datetime
from .. import database, models
from ..models import Task, TaskStatus, TaskType, Priority

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
        raise HTTPException(status_code=404, detail="MEETING_NOT_FOUND")
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

def _normalize_people_list(v) -> list[str]:
    if v is None: return []
    if isinstance(v, list): items = v
    elif isinstance(v, str):
        import re
        items = [x.strip() for x in re.split(r"[,\n;/]+", v) if x.strip()]
    else: return []
    seen, out = set(), []
    for x in items:
        if x and x not in seen:
            seen.add(x); out.append(x)
    return out

def _is_vote_open_for_task(task: Task) -> bool:
    # close_vote 시 status=DONE 이므로 바로 닫힘 처리
    if task.status == TaskStatus.DONE:
        return False
    ca = _get_vote_close_at_from_task(task)
    if not ca:
        return True
    try:
        return datetime.now() < datetime.fromisoformat(ca)  # 로컬 naive 비교(당신의 vote.py와 동일)
    except Exception:
        return True
def _get_vote_close_at_from_task(task: Task):
    dj = getattr(task, "details_json", None) or {}
    v  = dj.get("vote") or {}
    return v.get("close_at")

def _is_vote_open_for_task(task: Task) -> bool:
    # close_vote 시 status=DONE 이므로 바로 닫힘 처리
    if task.status == TaskStatus.DONE:
        return False
    ca = _get_vote_close_at_from_task(task)
    if not ca:
        return True
    try:
        return datetime.now() < datetime.fromisoformat(ca)  # 로컬 naive 비교(당신의 vote.py와 동일)
    except Exception:
        return True


# ── converters ────────────────────────────────────────────────────────────
status_from_str = enum_conv(models.TaskStatus, aliases={"cancelled": "canceled"}, lower=True)
type_from_str   = enum_conv(models.TaskType,  lower=False)  # "일반","체크리스트","데이터 취합","투표"
prio_from_str   = enum_conv(models.Priority,  lower=False)  # "낮음","보통","높음","긴급"

# ── PATCH 핸들러 ──────────────────────────────────────────────────────────

@router.patch("/{meeting_id}/actions/{task_id}")
def update_task(
    meeting_id: str,
    task_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    # 미팅 존재 확인
    require_meeting(db, meeting_id)

    t: Task | None = (
        db.query(Task)
          .filter(Task.id == task_id, Task.meeting_id == meeting_id)
          .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail="TASK_NOT_FOUND")

    # 문자열 필드
    if "title" in payload: t.title = (payload.get("title") or "").strip()[:512]
    if "note"  in payload: t.note  = payload.get("note")

    # 상태
    if "status" in payload:
        m = (payload.get("status") or "").lower()
        t.status = {
            "todo":        TaskStatus.TODO,
            "in_progress": TaskStatus.IN_PROGRESS,
            "feedback":    TaskStatus.FEEDBACK,
            "on_hold":     TaskStatus.ON_HOLD,
            "canceled":    TaskStatus.CANCELED,
            "cancelled":   TaskStatus.CANCELED,
            "done":        TaskStatus.DONE,
        }.get(m, t.status)

    # 유형

    if "task_type" in payload:
        tt_raw = (payload.get("task_type") or "").strip()
        tt_map = {
            "일반": TaskType.GENERAL, "general": TaskType.GENERAL, "GENERAL": TaskType.GENERAL,
            "체크리스트": TaskType.CHECKLIST, "checklist": TaskType.CHECKLIST, "CHECKLIST": TaskType.CHECKLIST,
            "데이터 취합": TaskType.COLLECT, "collect": TaskType.COLLECT, "COLLECT": TaskType.COLLECT,
            "투표": TaskType.VOTE, "vote": TaskType.VOTE, "VOTE": TaskType.VOTE,
        }
        new_tt = tt_map.get(tt_raw, None)

        if new_tt is not None:
            if t.task_type == TaskType.VOTE and new_tt != TaskType.VOTE:
                # ✅ '존재'가 아니라 '열려 있는지'만 체크
                if _is_vote_open_for_task(t):
                    raise HTTPException(409, "cannot change task_type from VOTE while vote is open")
                # 닫혀 있으면 전환 허용
            t.task_type = new_tt
        # new_tt가 None(엉뚱한 값)이면 무시 → 기존 타입 유지


    # 날짜 (YYYY-MM-DD)
    if "start_date"     in payload: t.start_date     = _parse_date(payload.get("start_date"))
    if "end_date"       in payload: t.end_date       = _parse_date(payload.get("end_date"))
    if "due_date"       in payload: t.due_date       = _parse_date(payload.get("due_date"))
    if "completed_date" in payload: t.completed_date = _parse_date(payload.get("completed_date"))

    # 작업 시간 ("1:30" 또는 "90")
    if "work_time" in payload:
        raw = (payload.get("work_time") or "").strip()
        mins = 0
        if ":" in raw:
            hh, mm = (raw.split(":") + ["0","0"])[:2]
            mins = int(hh or 0)*60 + int(mm or 0)
        elif raw.isdigit():
            mins = int(raw)
        t.work_time_min = max(0, mins)

    # 다중 선택(JSON)
    if "assignees" in payload:
        t.assignees_json = _normalize_people_list(payload.get("assignees")) or None

    # 🔹 watchers: 사용자가 보낸 경우에만 수정 (안 보내면 현 상태 유지)
    if "watchers" in payload:
        t.watchers_json = _normalize_people_list(payload.get("watchers")) or None

    # 우선순위 (옵션: Enum 사용 중일 때)
    if "priority" in payload and hasattr(t, "priority"):
        try:
            mapping = {"낮음": Priority.LOW, "보통": Priority.NORMAL, "높음": Priority.HIGH, "긴급": Priority.URGENT}
            p = payload.get("priority")
            t.priority = mapping.get(p, t.priority)
        except Exception:
            pass

    # 프로젝트 (모델에 있으면)
    if "project" in payload and hasattr(t, "project"):
        t.project = payload.get("project")

    db.commit(); db.refresh(t)

    return {
        "id": t.id,
        "title": t.title,
        "note": t.note,
        "status": t.status.value,
        "status_label": t.status.label() if hasattr(t.status, "label") else t.status.value,
        "task_type": t.task_type.value if hasattr(t.task_type, "value") else t.task_type,
        "start_date": t.start_date.isoformat() if t.start_date else None,
        "end_date": t.end_date.isoformat() if t.end_date else None,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "completed_date": t.completed_date.isoformat() if t.completed_date else None,
        "work_time_min": t.work_time_min,
        "assignees_json": t.assignees_json,
        "watchers_json": t.watchers_json,
        "priority": getattr(t.priority, "value", t.priority) if hasattr(t, "priority") else None,
        "project": getattr(t, "project", None),
    }