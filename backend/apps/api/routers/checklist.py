# apps/api/routers/checklist.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from .meetings import get_db
from .. import models, schemas

router = APIRouter(tags=["checklist"])

def _get_task_or_404(db: Session, mid: str, task_id: int) -> models.Task:
    task = db.get(models.Task, task_id)
    if not task or str(task.meeting_id) != str(mid):
        raise HTTPException(404, "task not found")
    if task.task_type != models.TaskType.체크리스트:
        raise HTTPException(409, "task is not checklist type")
    return task

def _recalc_task_status(db: Session, task: models.Task):
    # 모든 항목 완료 → done, 일부 완료 → in_progress, 0개 완료 → todo
    done_count = db.query(func.count(models.ChecklistItem.id))\
                   .filter_by(task_id=task.id, is_done=True).scalar()
    total = db.query(func.count(models.ChecklistItem.id))\
              .filter_by(task_id=task.id).scalar()
    new_status = (
        models.TaskStatus.done if total > 0 and done_count == total else
        (models.TaskStatus.in_progress if done_count > 0 else models.TaskStatus.todo)
    )
    if task.status != new_status:
        task.status = new_status
        db.add(task)

@router.get("/meetings/{mid}/actions/{task_id}/checklist-items",
            response_model=list[schemas.ChecklistItemOut])
def list_items(mid: str, task_id: int, db: Session = Depends(get_db)):
    _get_task_or_404(db, mid, task_id)
    items = (db.query(models.ChecklistItem)
               .filter_by(task_id=task_id)
               .order_by(models.ChecklistItem.order.asc(), models.ChecklistItem.id.asc())
               .all())
    return items

@router.post("/meetings/{mid}/actions/{task_id}/checklist-items",
             response_model=schemas.ChecklistItemOut, status_code=201)
def add_item(mid: str, task_id: int, payload: schemas.ChecklistItemCreate, db: Session = Depends(get_db)):
    task = _get_task_or_404(db, mid, task_id)
    max_order = db.query(func.coalesce(func.max(models.ChecklistItem.order), 0))\
                  .filter_by(task_id=task_id).scalar()
    item = models.ChecklistItem(task_id=task.id, label=payload.label, order=max_order + 1)
    db.add(item)
    db.commit(); db.refresh(item)
    # done 상태였으면 새 항목으로 todo로 되돌림
    if task.status == models.TaskStatus.done:
        task.status = models.TaskStatus.todo
        db.add(task); db.commit()
    return item

@router.patch("/meetings/{mid}/actions/{task_id}/checklist-items/{item_id}",
              response_model=schemas.ChecklistItemOut)
def update_item(mid: str, task_id: int, item_id: int, payload: schemas.ChecklistItemUpdate,
                db: Session = Depends(get_db)):
    task = _get_task_or_404(db, mid, task_id)
    item = db.get(models.ChecklistItem, item_id)
    if not item or item.task_id != task.id:
        raise HTTPException(404, "item not found")

    if payload.label is not None:
        item.label = payload.label
    if payload.order is not None:
        item.order = payload.order
    if payload.is_done is not None:
        item.is_done = payload.is_done

    db.add(item)
    _recalc_task_status(db, task)
    db.commit(); db.refresh(item)
    return item

@router.delete("/meetings/{mid}/actions/{task_id}/checklist-items/{item_id}", status_code=204)
def delete_item(mid: str, task_id: int, item_id: int, db: Session = Depends(get_db)):
    task = _get_task_or_404(db, mid, task_id)
    item = db.get(models.ChecklistItem, item_id)
    if not item or item.task_id != task.id:
        raise HTTPException(404, "item not found")
    db.delete(item)
    _recalc_task_status(db, task)
    db.commit()