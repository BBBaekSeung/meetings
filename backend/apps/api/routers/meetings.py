from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query, Request, Body, Response
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, select
from datetime import datetime, timedelta, timezone
from datetime import date as _date
import os, uuid, tempfile, json, base64, io, qrcode
import shutil
from typing import Literal,  Optional, List, Dict, Any
import logging
from pathlib import Path
import subprocess
import re as _re
# 파일 상단 근처에 헬퍼 추가


logger = logging.getLogger("app.meetings")


# ffmpeg 쓰면: import subprocess
from .. import database, models, clova_service
from ..schemas import MeetingCreateResponse, MeetingStatusResponse
from ..clova_service import transcribe_audio
from ..llm_service import summarize_and_extract
from ..task_classifier import classify_task_type
from ..models import Task, TaskType, TaskStatus, Priority
from .fullscript import normalize_segments, to_lines





router = APIRouter(prefix="/meetings")





# ---- 설정 값 ----
ALLOWED_CT = {
    "audio/wav", "audio/x-wav",
    "audio/mpeg",               # mp3
    "audio/aac","audio/x-m4a", # ← 추가
    "video/mp4",
    "audio/ogg", "audio/webm",
        "application/octet-stream",   # ✅ 추가: MediaRecorder가 자주 씀

}
MAX_UPLOAD_MB  = int(os.getenv("MAX_UPLOAD_MB", "200"))
UPLOAD_TTL_SEC = int(os.getenv("UPLOAD_TTL_SEC", "1200"))  # 20분

def _qr_data_uri(s: str) -> str:
    buf = io.BytesIO()
    qrcode.make(s).save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


# 파일 상단 공용 헬퍼로 빼기
def _parse_date(s):
    if not s:
        return None
    try:
        y, m, d = s.split("-")
        return _date(int(y), int(m), int(d))
    except Exception:
        return None


# === [추가] 청크 저장 루트 ===
UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", str(Path(tempfile.gettempdir()) / "smart-minutes")))

def _meeting_parts_dir(meeting_id: str) -> Path:
    return UPLOAD_ROOT / meeting_id / "parts"

def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

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

def _all_assignees_for_meeting(db: Session, meeting_id: str) -> set[str]:
    tasks = db.query(Task).filter(Task.meeting_id == meeting_id).all()
    s: set[str] = set()
    for t in tasks:
        for p in _normalize_people_list(t.assignees_json or []):
            s.add(p)
    return s

def _calc_watchers_for_task(all_assignees: set[str], t: Task) -> list[str]:
    own = set(_normalize_people_list(t.assignees_json or []))
    return sorted(list(all_assignees - own))




def _next_default_name(db) -> str:
    base = "나의 회의"
    # 해당 prefix로 시작하는 이름들 가져와 숫자 suffix 최대값 찾기
    rows = db.query(models.Meeting.name).filter(models.Meeting.name.like(f"{base}%")).all()
    mx = 0
    for (nm,) in rows:
        m = _re.fullmatch(rf"{base}(\d+)", str(nm).strip())
        if m:
            mx = max(mx, int(m.group(1)))
        elif nm == base:
            mx = max(mx, 1)
    # 1부터 시작: base(=나의 회의)도 이미 있으면 2부터
    return f"{base}{mx+1}" if rows else f"{base}1"

# 파일 상단 util 근처에 추가
import json, time, threading
_manifest_lock = threading.Lock()

def _manifest_path(meeting_id: str) -> Path:
    return _meeting_parts_dir(meeting_id) / "manifest.json"

def _load_manifest(meeting_id: str) -> dict:
    p = _manifest_path(meeting_id)
    if not p.exists():
        return {"received": [], "bytes": 0, "first_seq": None, "last_seq": None, "updated_at": None, "content_types": {}}
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return {"received": [], "bytes": 0, "first_seq": None, "last_seq": None, "updated_at": None, "content_types": {}}

def _save_manifest(meeting_id: str, mf: dict):
    p = _manifest_path(meeting_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(mf, ensure_ascii=False, indent=2), "utf-8")


def _probe_duration_sec(path: str) -> float:
    import subprocess, json

    # 1) stream.duration 우선
    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=duration",
                "-of", "json",
                path
            ],
            stderr=subprocess.STDOUT
        ).decode("utf-8", "ignore")
        js = json.loads(out)
        dur = None
        for st in (js.get("streams") or []):
            d = st.get("duration")
            if d is not None:
                try:
                    dur = float(d)
                    break
                except Exception:
                    pass
        if dur is not None and dur > 0:
            return dur
    except Exception:
        pass

    # 2) format.duration 폴백
    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path
            ],
            stderr=subprocess.STDOUT
        ).decode("utf-8", "ignore").strip()
        return float(out) if out else 0.0
    except Exception:
        return 0.0

# 파일 상단 유틸 근처에 추가
def _wait_for_tmp_flush(dirpath: Path, timeout_sec: float = 3.0):
    import time
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        tmps = list(dirpath.glob("*.tmp"))
        if not tmps:
            return
        time.sleep(0.05)  # 50ms

# 파일 상단 유틸 근처에 추가
def _ffprobe_ok(path: Path) -> bool:
    try:
        out = subprocess.check_output(
            ["ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=codec_type","-of","csv=p=0",str(path)],
            stderr=subprocess.STDOUT
        ).decode("utf-8","ignore").strip()
        return bool(out)  # a:0 스트림을 읽을 수 있으면 OK
    except Exception:
        return False


def now_utc():
    return datetime.now(timezone.utc)


def _as_aware_utc(dt):
    if dt is None:
        return None
    # 이미 aware면 그대로, naive면 UTC로 간주
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

from zoneinfo import ZoneInfo

def to_tz(dt, tz="Asia/Seoul"):
    if dt is None:
        return None
    if dt.tzinfo is None:
        # DB/드라이버가 naive로 돌려준 경우 UTC로 가정
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo(tz)).isoformat()

# ---- DB 세션 DI ----
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_meeting(db: Session, meeting_id: str) -> models.Meeting:
    m = db.get(models.Meeting, str(meeting_id))  # ← PK가 String(36)이므로 str로!
    if not m:
        raise HTTPException(status_code=404, detail="UNKNOWN_MEETING")
    return m

# ========== 1) 회의 생성 ==========


@router.post(
    "", 
    status_code=201, 
    response_model=MeetingCreateResponse,
    response_model_exclude_none=True   # ← None은 응답에서 제거
)

def create_meeting(
    source: Literal["web","mobile"] = Query("web"),
    name: str | None = Query(None), 
    request: Request = None,
    db: Session = Depends(get_db),
):
    if not name or not name.strip():
        name = _next_default_name(db)         
    # base 후보값 (웹 루트) ─ 반드시 /api 없이!
    env_base = os.getenv("PUBLIC_BASE_URL") or os.getenv("WEB_ORIGIN")
    req_base = str(request.base_url) if request else None
    # req_base 에 /api 가 붙어 올 수 있으므로 제거
    def strip_api_suffix(u: str | None) -> str | None:
        if not u:
            return None
        u = u.rstrip("/")
        return u[:-4] if u.endswith("/api") else u
    env_base = strip_api_suffix(env_base)
    req_base = strip_api_suffix(req_base)

    m = models.Meeting(
        status=models.MeetingStatus.PENDING_UPLOAD,
        name=name.strip(),                              # 🔵 추가
        progress=0,
        upload_token=uuid.uuid4().hex[:16],
        token_expires_at=now_utc() + timedelta(seconds=UPLOAD_TTL_SEC),
    )
    db.add(m); db.commit(); db.refresh(m)

    resp = {
        "id": m.id,
        "name": m.name,
        "status": m.status,
        "upload_token": m.upload_token,
        "upload_token_expires_in": UPLOAD_TTL_SEC,
        "progress": m.progress,
        "mobile_url": None,
        "qr_data_uri": None,
    }

    base = None
    if source == "mobile":
        base = (env_base or req_base)
        if not base:
            # 최후 수단: Host 헤더로 구성 (proxy-headers 켜두었을 때 유효)
            host = request.headers.get("host", "")
            scheme = "https" if request.headers.get("x-forwarded-proto") == "https" else "http"
            base = f"{scheme}://{host}"
        mobile_url = f"{base}/handoff/m/upload?mid={m.id}&t={m.upload_token}"
        resp["mobile_url"] = mobile_url
        resp["qr_data_uri"] = _qr_data_uri(mobile_url)

    # ★ 로그 찍기 (토큰은 마스킹!)
    masked_token = (m.upload_token[:4] + "****") if m.upload_token else None
    logger.info(
        "create_meeting: source=%s base=%s (env_base=%s, req_base=%s) id=%s upload_token=%s",
        source, base, env_base, req_base, m.id, masked_token
    )

    return resp



@router.patch("/{meeting_id}")
def update_meeting(
    meeting_id: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    m = require_meeting(db, meeting_id)

    new_name = payload.get("name")
    if new_name and new_name.strip():
        m.name = new_name.strip()
        db.commit()
        db.refresh(m)

    return {
        "id": m.id,
        "name": m.name,
        "status": m.status,
        "progress": m.progress,
        "updated_at": m.updated_at,
    }




# task수정

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
        tt = payload.get("task_type") or ""
        t.task_type = {
            "일반":       TaskType.GENERAL,
            "체크리스트": TaskType.CHECKLIST,
            "데이터 취합": TaskType.COLLECT,
            "투표":       TaskType.VOTE,
        }.get(tt, t.task_type)

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

# ========== 2) 오디오 업로드 ==========
@router.post("/{meeting_id}/upload", status_code=202)
async def upload_audio(
    meeting_id: str,
    token: str = Form(...),
    file: UploadFile = File(...),
    background: BackgroundTasks = None,  # 2번에서 설명
    db: Session = Depends(get_db),
):
    try:
        m = require_meeting(db, meeting_id)

        # 1) 토큰/만료 검증
# upload_audio 내부
        exp = _as_aware_utc(m.token_expires_at)
        now = now_utc()  # aware UTC
        if not (m.upload_token and exp and token == m.upload_token and exp > now):
            raise HTTPException(status_code=403, detail="INVALID_OR_EXPIRED_TOKEN")

        # 2) 타입/용량 검증 (콘텐츠 타입 로그)
        ct = (file.content_type or "").lower()
        logger.info("upload_audio: content_type=%s filename=%s", ct, file.filename)
        if not (
            ct in ALLOWED_CT
            or ct.startswith("audio/")
            or ct.startswith("video/")
            or ct == "application/octet-stream"
            or ct == ""
        ):
            raise HTTPException(status_code=400, detail=f"UPLOAD_INVALID_TYPE:{ct}")

        # 3) 임시 저장
        suffix = os.path.splitext((file.filename or ""))[1] or ".bin"
        tmp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}{suffix}")
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f, length=8 * 1024 * 1024)

        if os.path.getsize(tmp_path) > MAX_UPLOAD_MB * 1024 * 1024:
            try: os.remove(tmp_path)
            except: pass
            raise HTTPException(status_code=400, detail="UPLOAD_TOO_LARGE")

        # 4) 상태/메타 갱신
        m.source_filename = file.filename
        m.status = models.MeetingStatus.PROCESSING
        m.progress = 10
        m.upload_token = None
        m.token_expires_at = None
        db.commit()

        # 5) 파이프라인
        if background is not None:
            background.add_task(_process_pipeline_db, str(m.id), tmp_path)
        else:
            # 혹시 모를 None 방지용 폴백
            import threading
            threading.Thread(target=_process_pipeline_db, args=(str(m.id), tmp_path), daemon=True).start()

        return {"accepted": True, "id": m.id}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("upload_audio failed")
        raise HTTPException(status_code=500, detail=f"UPLOAD_ERROR:{type(e).__name__}:{e}")



@router.post("/{meeting_id}/upload-token")
def issue_upload_token(meeting_id: str, db: Session = Depends(get_db)):
    m = require_meeting(db, meeting_id)

    # 이미 처리 중/완료면 재업로드 목적이 명확하지 않으므로 기본은 409
    if m.status not in (models.MeetingStatus.PENDING_UPLOAD,):
        raise HTTPException(status_code=409, detail="CANNOT_REISSUE_TOKEN_IN_CURRENT_STATE")

    m.upload_token = uuid.uuid4().hex[:16]
    m.token_expires_at = now_utc() + timedelta(seconds=UPLOAD_TTL_SEC)
    db.commit()
    db.refresh(m)
    return {
        "id": m.id,
        "upload_token": m.upload_token,
        "upload_token_expires_in": UPLOAD_TTL_SEC,
    }


# ========== 2-1) (준실시간) 청크 업로드 ==========
@router.post("/{meeting_id}/chunk", status_code=202)
async def upload_chunk(
    meeting_id: str,
    token: str = Form(...),
    seq: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    m = require_meeting(db, meeting_id)

    # 토큰/만료 검증
    exp = _as_aware_utc(m.token_expires_at)
    if not (m.upload_token and exp and token == m.upload_token and exp > now_utc()):
        raise HTTPException(status_code=403, detail="INVALID_OR_EXPIRED_TOKEN")
    # 타입 검증(간단히)
    ct_raw = (file.content_type or "")
    ct = ct_raw.split(";", 1)[0].strip().lower()
    if ct not in ALLOWED_CT:
        raise HTTPException(status_code=400, detail="UPLOAD_INVALID_TYPE")

    # 단일 스트림에 append
    meet_dir = UPLOAD_ROOT / meeting_id
    _ensure_dir(meet_dir)
    stream_path = meet_dir / "stream.webm"

    # tmp에 먼저 쓰고 원자적 append
    tmp_path = stream_path.with_suffix(".tmp")
    with tmp_path.open("wb") as f:
        shutil.copyfileobj(file.file, f, length=8 * 1024 * 1024)

    size = tmp_path.stat().st_size
    if size > MAX_UPLOAD_MB * 1024 * 1024:
        try: tmp_path.unlink()
        except: pass
        raise HTTPException(status_code=400, detail="UPLOAD_TOO_LARGE")

    # append
    with stream_path.open("ab") as out, tmp_path.open("rb") as src:
        shutil.copyfileobj(src, out, length=8 * 1024 * 1024)
    tmp_path.unlink(missing_ok=True)

    # (선택) 진행상태 갱신
    if m.status == models.MeetingStatus.PENDING_UPLOAD:
        m.status = models.MeetingStatus.PROCESSING
        m.progress = max(m.progress or 0, 10)
        db.commit()

    return {"accepted": True, "seq": seq, "size": size}
def _concat_convert_and_process_sync(meeting_id_str: str):
    parts_dir = _meeting_parts_dir(meeting_id_str)
    lock_path = parts_dir / "parts.lock.json"

    # 1) 스냅샷 우선 사용 (없으면 기존 glob 폴백)
    if lock_path.exists():
        try:
            paths = json.loads(lock_path.read_text("utf-8"))
            parts = [Path(p) for p in paths]
        except Exception:
            parts = sorted(parts_dir.glob("part_*.webm"))
    else:
        parts = sorted(parts_dir.glob("part_*.webm"))

    if not parts:
        raise RuntimeError("NO_PARTS")

    # 2) (선택) 간단 유효성 필터: 존재/최소 크기
    valid = []
    dropped = []
    MIN_BYTES = int(os.getenv("MIN_PART_BYTES", "2048"))

    for p in parts:
        try:
            if not p.exists():
                dropped.append((p.name, "missing"))
                continue
            sz = p.stat().st_size
            if sz < MIN_BYTES:
                dropped.append((p.name, f"too_small:{sz}"))
                continue
            if not _ffprobe_ok(p):
                dropped.append((p.name, "ffprobe_fail"))
                continue
            valid.append(p)
        except Exception as ex:
            dropped.append((p.name, f"stat_err:{ex}"))

    if dropped:
        logger.info("concat filter: dropped parts=%s", dropped)

    if not valid:
        raise RuntimeError("NO_VALID_PARTS")
    # 3) concat list 파일 작성
    list_path = parts_dir / "parts.txt"
    with list_path.open("w", encoding="utf-8") as f:
        for p in valid:
            f.write(f"file '{p.as_posix()}'\n")

    merged_dir = parts_dir.parent
    merged_wav  = merged_dir / "merged.wav"

    # 4) ‘복사(-c copy)’ 금지: 즉시 PCM 디코드 + 에러 관용
    subprocess.run(
        [
            "ffmpeg","-y",
            "-loglevel","error",                  # 에러만 출력
            "-fflags","+genpts+discardcorrupt",   # 손상 패킷 건너뛰기
            "-err_detect","ignore_err",           # 디코드 오류 무시
            "-analyzeduration","0",               # 빠른 분석
            "-probesize","32k",                   # 빠른 프로빙
            "-i", str(stream_path),
            "-ac","1","-ar","16000",
            "-c:a","pcm_s16le",
            str(merged_wav),
        ],
        check=True
    )

    # 5) (로그) 최종 길이 진단
    dur = _probe_duration_sec(str(merged_wav))
    logger.info("merged.wav duration=%.3f sec", dur)

    # 6) 파이프라인 후속 처리
    _process_pipeline_db(meeting_id_str, str(merged_wav))

    # 7) 청소 (lock은 남겨도 됨 — 필요시 주석 해제)
    try:
        list_path.unlink(missing_ok=True)
        # lock_path.unlink(missing_ok=True)
        for p in parts_dir.glob("part_*.webm"):
            p.unlink(missing_ok=True)
        parts_dir.rmdir()
    except Exception:
        pass



@router.post("/{meeting_id}/finalize", status_code=202)
async def finalize_recording(
    meeting_id: str,
    payload: dict = Body(...),
    background: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    token = (payload or {}).get("token")
    m = require_meeting(db, meeting_id)
    exp = _as_aware_utc(m.token_expires_at)
    if not (m.upload_token and exp and token == m.upload_token and exp > now_utc()):
        raise HTTPException(status_code=403, detail="INVALID_OR_EXPIRED_TOKEN")

    meet_dir = UPLOAD_ROOT / meeting_id
    stream_path = meet_dir / "stream.webm"
    if not stream_path.exists() or stream_path.stat().st_size < 1024:
        raise HTTPException(status_code=400, detail="NO_PARTS")

    # 상태 갱신 + 토큰 무효화
    m.source_filename = "merged.wav"
    m.status = models.MeetingStatus.PROCESSING
    m.progress = max(m.progress or 0, 20)
    m.upload_token = None
    m.token_expires_at = None
    db.commit()

    # 백그라운드로 변환/파이프라인
    def _convert_and_process():
        merged_wav = meet_dir / "merged.wav"
        subprocess.run(
            [
                "ffmpeg","-y",
                "-loglevel","error",
                "-i", str(stream_path),
                "-ac","1","-ar","16000","-c:a","pcm_s16le",
                str(merged_wav),
            ],
            check=True
        )
        _process_pipeline_db(str(m.id), str(merged_wav))
        try:
            stream_path.unlink(missing_ok=True)  # 정리 (원하면 유지)
        except: pass

    if background is not None:
        background.add_task(_convert_and_process)
    else:
        import threading
        threading.Thread(target=_convert_and_process, daemon=True).start()

    return {"accepted": True, "id": m.id}



# meetings.py 상단에 유틸 추가
def _normalize_actions(raw):
    import json, re
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return [{"title": raw, "owner": None, "due": None, "note": None, "status": "todo"}]
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []

    out = []
    for it in raw:
        if isinstance(it, str):
            it = {"title": it}
        if not isinstance(it, dict):
            continue

        title    = (it.get("title") or it.get("task") or "").strip()
        owner    = (it.get("owner") or it.get("assignee"))
        assignees= it.get("assignees")
        due      = (it.get("due") or it.get("due_date"))
        note     = it.get("note")
        status   = (it.get("status") or "todo").strip().lower()

        # ★ 새로: start_date 통과(YYYY-MM-DD만 허용)
        start_date = it.get("start_date")
        if isinstance(start_date, str) and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", start_date.strip()):
            start_date = None

        if isinstance(due, str) and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due.strip()):
            due = None

        if title:
            out.append({
                "title": title[:512],
                "owner": (owner.strip() if isinstance(owner, str) else owner) or None,
                "assignees": assignees if (assignees is None or isinstance(assignees, (str, list))) else None,
                "due": due,
                "note": note if (note is None or isinstance(note, str)) else None,
                "status": status if status in {"todo","in_progress","feedback","on_hold","canceled","cancelled","done"} else "todo",
                "start_date": start_date,   # ← 유지!
            })
    return out



def _process_pipeline_db(meeting_id_str: str, tmp_path: str):
    SessionLocal = database.SessionLocal

    def set_state(status=None, progress=None, result=None, error=None):
        with SessionLocal() as sdb:
            mm = sdb.get(models.Meeting, meeting_id_str)
            if not mm:
                return
            if status is not None:
                mm.status = status
            if progress is not None:
                mm.progress = progress
            if result is not None:
                mm.result = result if isinstance(result, dict) else {"raw": result}
            if error is not None:
                base = mm.result if isinstance(mm.result, dict) else {}
                base["error"] = error
                mm.result = base
            sdb.commit()

    try:
        # ① 시작
        set_state(progress=30, status=models.MeetingStatus.PROCESSING)

        # ② 음성 인식
        text, segments = transcribe_audio(tmp_path)
        if not isinstance(segments, list):
            segments = []

        # ③ 중간 진행 표시
        set_state(progress=70)

        # ④ 요약/액션 추출 (dict 바로 전달)
        try:
# ✅ 다시 문자열로 전달
            payload_json = json.dumps({"transcript": text, "segments": segments}, ensure_ascii=False)
            llm_raw = summarize_and_extract(payload_json)
            llm = json.loads(llm_raw) if isinstance(llm_raw, str) else (llm_raw or {})

            summary = (llm.get("summary") or ["요약 없음"]) if isinstance(llm, dict) else ["요약 없음"]
            actions = llm.get("actions", []) if isinstance(llm, dict) else []

            # 액션 정규화(형식 튼튼하게)
            actions = _normalize_actions(actions)

            # 규칙 기반 태스크 타입 분류
            for a in actions:
                a["task_type"] = classify_task_type(a.get("title") or "")
        except Exception as e:
            summary, actions = (["(요약 생성 실패)"], [])

        # ⑤ DB 테이블에 액션 저장 (실패해도 계속)
        try:
            _save_tasks_table(meeting_id_str, actions)
        except Exception:
            logger.exception("[save_tasks_table] error")

        # ⑥ 완료 저장 (progress=90 커밋은 생략)
        result = {
            "transcript": text,
            "segments": segments,
            "summary": summary,
            "actions": actions,
        }
        set_state(status=models.MeetingStatus.COMPLETED, progress=100, result=result)

    except Exception as e:
        logger.exception("Error in pipeline for %s", meeting_id_str)
        set_state(status=models.MeetingStatus.FAILED, progress=100, error=str(e))
    finally:
        try:
            os.remove(tmp_path)
        except:
            pass

# ========== 3) 상태/결과 조회 ==========


def _serialize_task_row(t: Task) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "note": t.note,
        "status": t.status.value if hasattr(t.status, "value") else t.status,
        "status_label": t.status.label() if hasattr(t.status, "label") else None, 
        "task_type": t.task_type.value if hasattr(t.task_type, "value") else t.task_type,
        "start_date": t.start_date.isoformat() if t.start_date else None,
        "end_date": t.end_date.isoformat() if t.end_date else None,
        "due": t.due_date.isoformat() if t.due_date else None,
        "completed_date": t.completed_date.isoformat() if t.completed_date else None,
        "work_time_min": t.work_time_min,
        # 🔹 프론트가 쓰는 필드들
        "assignees_json": t.assignees_json or [],
        "watchers_json": t.watchers_json or [],
        "priority": getattr(t.priority, "value", t.priority) if hasattr(t, "priority") else None,
        "project": getattr(t, "project", None),
    }

@router.get("/{meeting_id}")
def get_meeting(meeting_id: str, view: str | None = None, db: Session = Depends(get_db)):
    m = db.get(models.Meeting, meeting_id)
    if not m:
        raise HTTPException(404, "meeting not found")

    base = {
        "id": m.id,
        "status": getattr(m.status, "value", m.status),
        "name": m.name,
        "progress": m.progress,
        "source_filename": m.source_filename,
        "created_at": m.created_at,
        "updated_at": m.updated_at,
    }

    # 완료/실패 시 result 포함
    if getattr(m, "result", None):
        base["result"] = m.result  # JSONUnicode면 그대로 문자열/딕셔너리

    if view == "full":
        # actions(tasks) 안전 조회
        tasks = db.execute(
            select(models.Task).where(models.Task.meeting_id == meeting_id)
        ).scalars().all()
        base["actions"] = [_serialize_task_row(t) for t in tasks]


        # (선택) 체크리스트 미리 합치기 — 관계가 없어도 안전
        try:
            task_ids = [t.id for t in tasks]
            if hasattr(models, "ChecklistItem") and task_ids:
                rows = db.execute(
                    select(models.ChecklistItem).where(models.ChecklistItem.task_id.in_(task_ids))
                ).scalars().all()
                by_task = {}
                for r in rows:
                    by_task.setdefault(r.task_id, []).append({
                        "id": r.id, "label": r.label, "is_done": r.is_done, "order": r.order
                    })
                for a in base["actions"]:
                    if a["task_type"] == "체크리스트":
                        a["checklist_items"] = by_task.get(a["id"], [])
        except Exception:
            # 체크리스트 테이블이 아직 없거나 오류면 조용히 스킵
            pass

    return base

# meetings.py 맨 아래쪽에 추가 (import는 파일 위에 적절히 배치)
def _save_tasks_table(meeting_id_str: str, actions: list[dict]):
    SessionLocal = database.SessionLocal
    with SessionLocal() as sdb:
        sdb.query(Task).filter(Task.meeting_id == meeting_id_str).delete()

        rows = []
        for a in actions or []:
            assignees = _normalize_people_list(
                a.get("assignees") or
                ([a.get("owner")] if a.get("owner") else [])   # 과거 owner 단일도 흡수
            )
            rows.append(Task(
                meeting_id   = meeting_id_str,
                title        = (a.get("title") or "").strip()[:512],
                assignee     = None,                 # ✅ 더이상 사용하지 않음(레거시)
                assignees_json = assignees or None,  # ✅ 핵심
                start_date   = _parse_date(a.get("start_date")),
                due_date     = _parse_date(a.get("due")),
                note         = a.get("note") or None,
            status = {
                "todo": TaskStatus.TODO,
                "in_progress": TaskStatus.IN_PROGRESS,
                "feedback": TaskStatus.FEEDBACK,
                "on_hold": TaskStatus.ON_HOLD,
                "canceled": TaskStatus.CANCELED,
                "cancelled": TaskStatus.CANCELED,
                "done": TaskStatus.DONE,
            }.get((a.get("status") or "").lower(), TaskStatus.TODO),
                task_type    = {
                    "일반": TaskType.GENERAL, "체크리스트": TaskType.CHECKLIST,
                    "데이터 취합": TaskType.COLLECT, "투표": TaskType.VOTE,
                }.get(a.get("task_type") or "", TaskType.GENERAL),
            ))

        if rows:
            sdb.bulk_save_objects(rows)
        sdb.commit()

        # 🔹 초기값: 전체 태스크 watchers 자동 채움
        tasks = sdb.query(Task).filter(Task.meeting_id == meeting_id_str).all()
        allset = _all_assignees_for_meeting(sdb, meeting_id_str)
        for t in tasks:
            t.watchers_json = _calc_watchers_for_task(allset, t) or None
        sdb.commit()


# meetings.py 상단 import 보강
from typing import Literal

# meetings.py 어딘가(생성/업로드들 사이 아무데나) 추가
@router.get("")  # ← prefix "/meetings" + "" = "/meetings"
def list_meetings(
    view: Literal["brief", "full"] = Query("brief"),
    order: Literal["asc", "desc"] = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(models.Meeting)

    # 정렬
    q = q.order_by(
        models.Meeting.created_at.desc() if order == "desc"
        else models.Meeting.created_at.asc()
    )

    # 개수 제한
    q = q.limit(limit)

    rows = q.all()
    out = []
    for m in rows:
        item = {
            "id": m.id,
            "name": m.name,
            "status": getattr(m.status, "value", m.status),  # ✅ 여기 수정
            "progress": m.progress,
    "created_at": to_tz(m.created_at),
    "updated_at": to_tz(m.updated_at),
        }
        # 목록은 가볍게: 필요하면 full일 때 summary/actions만 포함
        if view == "full" and m.status in (models.MeetingStatus.COMPLETED, models.MeetingStatus.FAILED):
            src = m.result if isinstance(m.result, dict) else {}
            actions_db = [
                _serialize_task_row(t)
                for t in db.query(Task)
                        .filter(Task.meeting_id == m.id)
                        .order_by(Task.id.asc())
                        .all()
            ]
            item["result"] = {
                "summary": src.get("summary"),
                "actions": actions_db,  # ✅ DB 최신값
            }
        out.append(item)
    return out



@router.get("/{meeting_id}/fullscript", response_class=Response)
def get_fullscript_text(
    meeting_id: str,
    db: Session = Depends(get_db),
    merge_consecutive: bool = Query(True, description="같은 화자의 연속 발화를 한 줄로 병합할지 여부 (기본: true)"),
):
    mt: models.Meeting = db.get(models.Meeting, meeting_id)
    if not mt:
        raise HTTPException(404, "Meeting not found")
    if not mt.result:
        raise HTTPException(409, "Result not ready")

    try:
        result: Dict[str, Any] = mt.result if isinstance(mt.result, dict) else json.loads(mt.result)
    except Exception:
        raise HTTPException(500, "Invalid result format")

    segments = result.get("segments") or []
    if not isinstance(segments, list):
        raise HTTPException(500, "segments missing or invalid")

    norm = normalize_segments(segments)
    lines = to_lines(norm, merge=merge_consecutive)
    text_body = "\n".join(lines)

    return Response(content=text_body, media_type="text/plain; charset=utf-8")


@router.get("/{meeting_id}/fullscript.json")
def get_fullscript_json(
    meeting_id: str,
    db: Session = Depends(get_db),
    merge_consecutive: bool = Query(True, description="같은 화자의 연속 발화를 한 줄로 병합할지 여부 (기본: true)"),
):
    mt: models.Meeting = db.get(models.Meeting, meeting_id)
    if not mt:
        raise HTTPException(404, "Meeting not found")
    if not mt.result:
        raise HTTPException(409, "Result not ready")

    try:
        result: Dict[str, Any] = mt.result if isinstance(mt.result, dict) else json.loads(mt.result)
    except Exception:
        raise HTTPException(500, "Invalid result format")

    segments = result.get("segments") or []
    if not isinstance(segments, list):
        raise HTTPException(500, "segments missing or invalid")

    norm = normalize_segments(segments)
    lines = to_lines(norm, merge=merge_consecutive)

    # UI에서 줄 단위로 렌더하기 쉽게 JSON 배열로 반환
    return {
        "meeting_id": meeting_id,
        "merge_consecutive": merge_consecutive,
        "lines": lines,  # ["참가자1: ...", "참가자2: ...", ...]
        "count": len(lines),
    }
