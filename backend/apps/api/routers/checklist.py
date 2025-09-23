# apps/api/routers/checklist.py
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Action, ChecklistItem  # 실제 경로/이름에 맞게
# ------------------------------------------------------------

router = APIRouter(prefix="/meetings", tags=["checklist"])

# Pydantic 스키마 (응답 직렬화 OK 하려면 orm_mode 필수)
class ChecklistItemOut(BaseModel):
    id: int
    label: str
    is_done: bool
    order: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class ChecklistCreate(BaseModel):
    label: str

# 회의-액션 소속 검증
def _ensure_task_in_meeting(db: Session, mid: str, task_id: int) -> Action:
    task = db.query(Action).filter(
        Action.id == task_id,
        Action.meeting_id == mid
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found in this meeting")
    return task

@router.get("/{mid}/actions/{task_id}/checklist-items", response_model=List[ChecklistItemOut])
def list_items(mid: str, task_id: int, db: Session = Depends(get_db)):
    _ensure_task_in_meeting(db, mid, task_id)
    items = (db.query(ChecklistItem)
               .filter(ChecklistItem.task_id == task_id)
               .order_by(
                   ChecklistItem.order.is_(None),  # order 있는 것 먼저
                   ChecklistItem.order.asc(),
                   ChecklistItem.id.asc(),
               )
               .all())
    return items

@router.post("/{mid}/actions/{task_id}/checklist-items",
             response_model=ChecklistItemOut,
             status_code=status.HTTP_201_CREATED)
def create_item(mid: str, task_id: int, body: ChecklistCreate, db: Session = Depends(get_db)):
    _ensure_task_in_meeting(db, mid, task_id)

    # 안전한 order 할당
    max_order = (db.query(func.max(ChecklistItem.order))
                   .filter(ChecklistItem.task_id == task_id)
                   .scalar())
    next_order = (max_order or 0) + 1

    item = ChecklistItem(
        task_id=task_id,
        label=body.label,
        is_done=False,
        order=next_order,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item



class ChecklistPatch(BaseModel):
    label: Optional[str] = None
    is_done: Optional[bool] = None
    order: Optional[int] = None

@router.patch("/{mid}/actions/{task_id}/checklist-items/{item_id}",
              response_model=ChecklistItemOut)
def patch_item(mid: str, task_id: int, item_id: int,
               body: ChecklistPatch, db: Session = Depends(get_db)):
    _ensure_task_in_meeting(db, mid, task_id)

    item = (db.query(ChecklistItem)
              .filter(ChecklistItem.id == item_id,
                      ChecklistItem.task_id == task_id)
              .first())
    if not item:
        raise HTTPException(status_code=404,
                            detail=f"Checklist item not found: {item_id}")

    if body.label is not None:
        item.label = body.label
    if body.is_done is not None:
        item.is_done = body.is_done
    if body.order is not None:
        item.order = body.order

    db.commit()
    db.refresh(item)
    return item

@router.delete("/{mid}/actions/{task_id}/checklist-items/{item_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def delete_item(mid: str, task_id: int, item_id: int, db: Session = Depends(get_db)):
    _ensure_task_in_meeting(db, mid, task_id)
    deleted = (db.query(ChecklistItem)
                 .filter(ChecklistItem.id == item_id,
                         ChecklistItem.task_id == task_id)
                 .delete())
    if not deleted:
        raise HTTPException(status_code=404,
                            detail=f"Checklist item not found: {item_id}")
    db.commit()
    return None