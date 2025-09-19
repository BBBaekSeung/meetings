# apps/api/models.py
import enum, uuid, json
from datetime import datetime, date, timezone
from sqlalchemy import (
    Column, String, DateTime, Integer, Date,
    ForeignKey, Index
)
from sqlalchemy.types import TypeDecorator, TEXT
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SAEnum
from .database import Base
from sqlalchemy.orm import deferred


def _uuid() -> str:
    return str(uuid.uuid4())

class JSONUnicode(TypeDecorator):
    impl = TEXT
    cache_ok = True
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return json.loads(value)
        except Exception:
            # 👇 깨진 JSON이거나 이미 dict/list가 아닌 경우, 그대로 문자열로 두지 말고
            # 최소한 호출부에서 방어하도록 원문을 그대로 돌려보내되,
            # 이후 summarize/get 시에는 ensure_obj 같은 방어 유틸을 써서 dict로 강제하세요.
            return value


# ── Enums ─────────────────────────────────────────
class MeetingStatus(str, enum.Enum):
    PENDING_UPLOAD = "pending_upload"
    PROCESSING     = "processing"
    COMPLETED      = "completed"
    FAILED         = "failed"

    def label(self) -> str:
        return {
            "pending_upload": "대기",
            "processing": "처리중",
            "completed": "완료",
            "failed": "실패",
        }[self.value]
    
class TaskStatus(str, enum.Enum):
    TODO        = "todo"
    IN_PROGRESS = "in_progress"
    FEEDBACK    = "feedback"
    ON_HOLD     = "on_hold"
    CANCELED    = "canceled"
    DONE        = "done"

    def label(self) -> str:
        return {
            "todo": "대기",
            "in_progress": "진행",
            "feedback": "피드백",
            "on_hold": "보류",
            "canceled": "취소",
            "done": "완료",
        }[self.value]

class TaskType(str, enum.Enum):
    GENERAL     = "일반"
    CHECKLIST   = "체크리스트"
    COLLECT     = "데이터 취합"
    VOTE        = "투표"

# ✅ Priority는 여기(사용 전에) 정의해야 함
class Priority(str, enum.Enum):
    LOW="낮음"; NORMAL="보통"; HIGH="높음"; URGENT="긴급"

# ── Models ────────────────────────────────────────
class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(String(36), primary_key=True, default=_uuid)
    status = Column(SAEnum(MeetingStatus, native_enum=False), nullable=False,
                    default=MeetingStatus.PENDING_UPLOAD)
    name = Column(String(200), nullable=False, index=True, default="나의 회의")
    progress = Column(Integer, nullable=False, default=0)
    source_filename = Column(String(512), nullable=True)
    result = deferred(Column(JSONUnicode, nullable=True))
    upload_token = Column(String(64), nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    actions = relationship("Task", back_populates="meeting", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    title      = Column(String(512), nullable=False)
    assignee   = Column(String(128), nullable=True)
    note       = Column(String(2000), nullable=True)

    # 날짜
    start_date     = Column(Date, nullable=False, default=date.today)
    end_date       = Column(Date, nullable=True)
    due_date       = Column(Date, nullable=True)
    completed_date = Column(Date, nullable=True)

    # 상태/유형/우선순위
    status    = Column(SAEnum(TaskStatus, native_enum=False), nullable=False, default=TaskStatus.TODO)
    task_type = Column(SAEnum(TaskType,    native_enum=False), nullable=False, default=TaskType.GENERAL)
    priority  = Column(SAEnum(Priority,    native_enum=False), nullable=True)

    # 시간(분)
    work_time_min = Column(Integer, nullable=False, default=0)

    # 다중 선택(JSON)
    watchers_json  = Column(JSONUnicode, nullable=True)   # ["Intern","Cloud Tech LABs"]
    assignees_json = Column(JSONUnicode, nullable=True)   # ["홍길동","김영희"]

    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    meeting  = relationship("Meeting", back_populates="actions")

# 인덱스(필요한 것만)
Index("ix_tasks_meeting_due", Task.meeting_id, Task.due_date)
Index("ix_tasks_status_updated", Task.status, Task.updated_at)
Index("ix_meetings_status_updated", Meeting.status, Meeting.updated_at)

# 호환용 별칭 (선택)
Action = Task

# 호환용 별칭 (기존 코드가 ActionStatus를 참조하는 곳을 위해)
ActionStatus = TaskStatus


