# apps/api/schemas.py

from datetime import datetime, date
from pydantic import BaseModel
from typing import Any, List, Optional
from .models import TaskStatus, TaskType

from .models import MeetingStatus, Priority  # noqa: F401

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


class MeetingCreateResponse(BaseConfig):
    id: str
    status: MeetingStatus
    upload_token: str | None
    upload_token_expires_in: int
    progress: int
    mobile_url: str | Optional[str] = None
    qr_data_uri: str | Optional[str] = None