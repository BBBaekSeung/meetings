# apps/api/schemas.py

from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, List, Optional
from .models import TaskStatus, TaskType, MeetingStatus, Priority 

class BaseConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# 공통 설정을 위한 부모 클래스
class BaseConfig(BaseModel):
    class Config:
        from_attributes = True
        use_enum_values = True

# POST /meetings 의 응답을 위한 스키마
class MeetingCreateResponse(BaseConfig):
    id: str
    name: str    
    status: MeetingStatus
    upload_token: str | None
    upload_token_expires_in: int
    progress: int
    

# GET /meetings/{id} 의 응답을 위한 스키마
class MeetingStatusResponse(BaseConfig):
    id: str
    name: str
    status: MeetingStatus
    progress: int
    source_filename: str | None
    created_at: datetime
    updated_at: datetime
    result: dict | None = None


class TaskBase(BaseModel):
    title: str
    status: TaskStatus
    task_type: TaskType

    assignee: Optional[str] = None          # 대표 담당자
    assignees: List[str] = []               # 다중 작업자 (assignees_json 매핑)
    watchers: List[str] = []                # 관람자 (watchers_json 매핑)
    note: Optional[str] = None

    # 날짜들
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    completed_date: Optional[date] = None
    due_date: Optional[date] = None

    # 시간/우선순위
    work_time_min: int = 0
    priority: Optional[Priority] = None

class TaskCreate(TaskBase):
    pass

class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


# ✅ 추가: 부분 업데이트 전용 (모든 필드 Optional)
class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[TaskStatus] = None
    task_type: Optional[TaskType] = None
    assignee: Optional[str] = None
    assignees: Optional[List[str]] = None
    watchers: Optional[List[str]] = None
    note: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    completed_date: Optional[date] = None
    due_date: Optional[date] = None
    work_time_min: Optional[int] = None
    priority: Optional[Priority] = None
    details_json: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)





class MeetingCreateResponse(BaseConfig):
    id: str
    status: MeetingStatus
    upload_token: str | None
    upload_token_expires_in: int
    progress: int
    mobile_url: str | Optional[str] = None
    qr_data_uri: str | Optional[str] = None

# -----------------------------
# Checklist schemas
# -----------------------------
class ChecklistItemOut(BaseModel):
    id: int
    label: str
    is_done: bool
    order: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ChecklistItemCreate(BaseModel):
    label: str

class ChecklistItemUpdate(BaseModel):
    label: Optional[str] = None
    is_done: Optional[bool] = None
    order: Optional[int] = None


# 투표기능
# apps/api/schemas.py (추가)
class VoteOptionCreate(BaseModel):
    label: str

class VoteOptionOut(BaseModel):
    id: int
    label: str
    votes: int

class VoteCastIn(BaseModel):
    voter: str
    option_id: int

# 저장(시작) 시 한 번에 받을 설정: 옵션 + 마감시각만
class VoteConfigIn(BaseModel):
    options: List[str] = Field(min_items=2)          # 2개 이상
    close_at: str | None = None               # 로컬 문자열 그대로

class VoteSummaryOut(BaseModel):
    is_open: bool
    close_at: str | None = None
    my_option_id: Optional[int] = None              # 이 투표자가 찍은 옵션(없으면 None)
    total_votes: int
    options: List[VoteOptionOut]