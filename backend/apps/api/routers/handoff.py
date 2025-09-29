# apps/api/routers/handoff.py
from fastapi import APIRouter, Depends, Body
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import os, uuid, urllib.parse
import base64, io
import qrcode
from pydantic import BaseModel

from .. import database, models

router = APIRouter(prefix="/handoff")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://15.164.234.96")
UPLOAD_TTL_SEC = int(os.getenv("UPLOAD_TTL_SEC", "1200"))

class StartReq(BaseModel):
    name: str | None = None

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()






@router.post("/start")
def start_handoff(payload: StartReq = Body(default=None), db: Session = Depends(get_db)):
    name = (payload.name or "").strip() if payload else None
    m = models.Meeting(
        name=name,  # ← 여기서 저장!
        status=models.MeetingStatus.PENDING_UPLOAD,
        progress=0,
        upload_token=uuid.uuid4().hex[:16],
        token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=UPLOAD_TTL_SEC),
    )
    db.add(m); db.commit(); db.refresh(m)

    q = urllib.parse.urlencode({"mid": str(m.id), "t": m.upload_token})
    # 기존 PUBLIC_BASE_URL 또는 요청에서 받은 base_url을 프런트 도메인으로 수정
    mobile_url = f"{PUBLIC_BASE_URL}/m/upload?{q}"  # /m/upload 경로로 변경
    buf = io.BytesIO()
    qrcode.make(mobile_url).save(buf, format="PNG")
    qr_data_uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "meeting_id": str(m.id),
        "upload_token": m.upload_token,
        "upload_token_expires_in": UPLOAD_TTL_SEC,
        "mobile_url": mobile_url,
        "qr_data_uri": qr_data_uri,  # ← 이것만 img src로 쓰면 됨
    }


@router.get("/m/upload", response_class=HTMLResponse)
def mobile_upload_page(mid: str, t: str):
    import json
    html = """
<!doctype html>
<html lang="ko"><meta name="viewport" content="width=device-width, initial-scale=1">
<body style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:16px;line-height:1.5">
<h3 style="margin:0 0 12px">녹음 업로드</h3>
<div style="font-size:13px;color:#6b7280;margin-bottom:8px">지원: wav, mp3, m4a, aac, mp4 (최대 200MB)</div>

<input id="file" type="file" accept="audio/*,video/mp4"/>
<button id="btn" style="margin-left:8px;padding:8px 14px;border:0;border-radius:8px;background:#111827;color:#fff">업로드</button>

<div id="barwrap" style="display:none;margin-top:16px;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
  <div id="bar" style="height:10px;width:0%;background:#16a34a;transition:width .2s"></div>
</div>

<pre id="log" style="white-space:pre-wrap;margin-top:12px"></pre>

<script>
const mid = __MID__;
const token = __TOKEN__;

const $ = (id)=>document.getElementById(id);
const log = (s)=>{$('log').textContent = s};
const btn = $('btn');
const file = $('file');
const barwrap = $('barwrap');
const bar = $('bar');

const ALLOWED = ['audio/wav','audio/x-wav','audio/mpeg','audio/mp4','audio/x-m4a','audio/aac','video/mp4'];
const MAX_MB = 200;

function setBusy(v){
  btn.disabled = v;
  btn.textContent = v ? '업로드 중…' : '업로드';
  btn.style.opacity = v ? .7 : 1;
}

async function pollStatus(){
  for (let i=0;i<180;i++){ // 2s * 180 = 6분
    try{
      const r = await fetch(`/meetings/${mid}`);
      if(!r.ok){ log(`상태 조회 오류: ${r.status}`); return; }
      const j = await r.json();
      const {status, progress, result} = j;

      barwrap.style.display = 'block';
      const pct = Math.max(0, Math.min(100, progress || 0));
      bar.style.width = pct + '%';

      if(status === 'COMPLETED'){
        log(
          `완료 (${pct}%)\\n\\n요약:\\n- ${result.summary.join('\\n- ')}\\n\\n` +
          `액션(${result.actions.length}개):\\n` +
          result.actions.map(a=>`• ${a.title} [${a.task_type}] ${a.owner ?? ''} ${a.due ?? ''}`).join('\\n')
        );
        return;
      }
      if(status === 'FAILED'){
        log('처리 실패:\\n' + JSON.stringify(result, null, 2));
        return;
      }
      log(`처리 중… ${pct}%`);
    }catch(e){
      log('상태 폴링 에러: ' + (e?.message || e));
      return;
    }
    await new Promise(r=>setTimeout(r, 2000));
  }
  log('시간 초과: 잠시 후 다시 확인해주세요.');
}

btn.onclick = async () => {
  const f = file.files[0];
  if(!f){ alert('파일을 선택하세요'); return; }
  if(f.size > MAX_MB*1024*1024){ alert(`파일이 너무 큽니다 (최대 ${MAX_MB}MB)`); return; }
  if(f.type && !ALLOWED.includes(f.type)){ alert('지원하지 않는 파일 형식입니다'); return; }

  const fd = new FormData();
  fd.append('token', token);
  fd.append('file', f, f.name);

  setBusy(true); log('업로드 중…');
  barwrap.style.display = 'none'; bar.style.width = '0%';

  try{
    const res = await fetch(`/meetings/${mid}/upload`, { method:'POST', body: fd });
    const text = await res.text();
    if(!res.ok){
      throw new Error(text || ('HTTP '+res.status));
    }
    log('업로드 완료! 처리 상태 확인 중…');
    await pollStatus();
  }catch(e){
    const msg = (e?.message || '').includes('INVALID_OR_EXPIRED_TOKEN')
      ? '토큰 만료/무효입니다. 새 링크를 발급하세요.'
      : (e?.message || '업로드 실패');
    log(msg + (e?.message ? `\\n\\n${e.message}` : ''));
  }finally{
    setBusy(false);
  }
};
</script>
</body></html>
"""
    # JS에서 안전하게 쓰도록 JSON 인코딩해서 끼워 넣기
    html = html.replace("__MID__", json.dumps(mid)).replace("__TOKEN__", json.dumps(t))
    return HTMLResponse(content=html, status_code=200)

