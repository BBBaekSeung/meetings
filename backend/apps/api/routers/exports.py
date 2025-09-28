# apps/api/routers/exports.py  (교체)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import database, models

router = APIRouter(prefix="/meetings")

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

@router.post("/{meeting_id}/exports")
def export_tasks_dummy(meeting_id: str, db: Session = Depends(get_db)):
    m = require_meeting(db, meeting_id)

    # MVP: tasks 테이블을 정본으로 사용
    tasks = db.query(models.Task).filter(models.Task.meeting_id == meeting_id).all()
    if not tasks:
        raise HTTPException(status_code=409, detail="NO_TASKS_TO_EXPORT")

    # 필요시 상태 필터링 (예: 취소 제외)
    exportables = [t for t in tasks if t.status != models.ActionStatus.CANCELED]

    items = [
        {"task_id": t.id, "external_id": f"DUMMY-{meeting_id[:6]}-{t.id}"}
        for t in exportables
    ]
    return {"exported_count": len(items), "items": items}
