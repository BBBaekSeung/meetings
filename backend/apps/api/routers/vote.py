# apps/api/routers/vote.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from .meetings import get_db
from .. import models, schemas
from datetime import datetime, timezone

router = APIRouter(tags=["vote"])

def _get_vote_task(db: Session, mid: str, task_id: int) -> models.Task:
    task = db.get(models.Task, task_id)
    if not task or str(task.meeting_id) != str(mid):
        raise HTTPException(404, "task not found")
    if task.task_type != models.TaskType.투표:
        raise HTTPException(409, "task is not vote type")
    return task

def _get_close_at(task: models.Task):
    dj = getattr(task, "details_json", None) or {}
    return ((dj.get("vote") or {}).get("close_at")) if isinstance(dj, dict) else None

def _is_open(task: models.Task):
    close_at = _get_close_at(task)
    if task.status == models.TaskStatus.done:
        return False
    if close_at:
        try:
            # naive 처리는 UTC로 본다(프론트에서 ISO8601 권장)
            ca = datetime.fromisoformat(close_at.replace("Z","+00:00"))
            return datetime.now(timezone.utc) < ca.astimezone(timezone.utc)
        except Exception:
            return True
    return True

@router.get("/meetings/{mid}/actions/{task_id}/vote", response_model=schemas.VoteSummaryOut)
def get_vote(mid: str, task_id: int, voter: str | None = None, db: Session = Depends(get_db)):
    task = _get_vote_task(db, mid, task_id)
    # 옵션 + 득표 집계
    opts = db.query(models.VoteOption).filter_by(task_id=task.id).all()
    counts = dict(db.query(models.VoteBallot.option_id, func.count(models.VoteBallot.id))
                    .filter(models.VoteBallot.task_id == task.id)
                    .group_by(models.VoteBallot.option_id).all())
    my = None
    if voter:
        my_row = db.query(models.VoteBallot).filter_by(task_id=task.id, voter=voter).first()
        my = my_row.option_id if my_row else None
    return schemas.VoteSummaryOut(
        is_open=_is_open(task),
        close_at=_get_close_at(task),
        my_option_id=my,
        total_votes=sum(counts.values()) if counts else 0,
        options=[schemas.VoteOptionOut(id=o.id, label=o.label, votes=int(counts.get(o.id,0))) for o in opts]
    )

@router.post("/meetings/{mid}/actions/{task_id}/vote/options",
             response_model=schemas.VoteOptionOut, status_code=201)
def add_option(mid: str, task_id: int, payload: schemas.VoteOptionCreate, db: Session = Depends(get_db)):
    task = _get_vote_task(db, mid, task_id)
    if not _is_open(task):
        raise HTTPException(409, "vote closed")
    o = models.VoteOption(task_id=task.id, label=payload.label)
    db.add(o); db.commit(); db.refresh(o)
    return schemas.VoteOptionOut(id=o.id, label=o.label, votes=0)

@router.delete("/meetings/{mid}/actions/{task_id}/vote/options/{option_id}", status_code=204)
def delete_option(mid: str, task_id: int, option_id: int, db: Session = Depends(get_db)):
    task = _get_vote_task(db, mid, task_id)
    if not _is_open(task):
        raise HTTPException(409, "vote closed")
    o = db.get(models.VoteOption, option_id)
    if not o or o.task_id != task.id:
        raise HTTPException(404, "option not found")
    # 이미 표가 있으면 삭제 제한(안전)
    has_votes = db.query(models.VoteBallot.id).filter_by(task_id=task.id, option_id=o.id).first()
    if has_votes:
        raise HTTPException(409, "option has votes")
    db.delete(o); db.commit()

@router.post("/meetings/{mid}/actions/{task_id}/vote/cast")
def cast_vote(mid: str, task_id: int, payload: schemas.VoteCastIn, db: Session = Depends(get_db)):
    task = _get_vote_task(db, mid, task_id)
    if not _is_open(task):
        raise HTTPException(409, "vote closed")
    opt = db.get(models.VoteOption, payload.option_id)
    if not opt or opt.task_id != task.id:
        raise HTTPException(404, "option not found")
    # 1인 1표: 중복 체크
    exists = db.query(models.VoteBallot.id).filter_by(task_id=task.id, voter=payload.voter).first()
    if exists:
        raise HTTPException(409, "already voted")
    # 투표 저장
    ballot = models.VoteBallot(task_id=task.id, option_id=opt.id, voter=payload.voter)
    db.add(ballot); db.commit()
    return {"ok": True}
