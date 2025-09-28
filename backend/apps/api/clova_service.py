import os, json, time, requests, re
from typing import Any, Dict, List, Optional, Tuple
SESSION = requests.Session()  # ★ 전역 세션 재사용


BASE_URL = os.getenv("CLOVA_SPEECH_INVOKE_URL", "").rstrip("/")
SECRET   = os.getenv("CLOVA_SPEECH_API_KEY", "")
LANG     = os.getenv("CLOVA_SPEECH_LANGUAGE", "ko-KR")

REQUEST_TIMEOUT = int(os.getenv("CLOVA_REQUEST_TIMEOUT", "900"))
POLL_INTERVAL   = float(os.getenv("CLOVA_POLL_INTERVAL", "3"))
POLL_TIMEOUT    = int(os.getenv("CLOVA_POLL_TIMEOUT", "1800"))


# === [유틸] speaker 정규화 ===============================================
def _norm_speaker(v: Any) -> Dict[str, Any] | None:
    """
    v 가 "1"/1/"A"/{"label":"1","name":"A"} 등 어떠한 형태든
    {"label": "1", "name":"A", "edited": False} 형태로 통일
    """
    if v is None:
        return None
    if isinstance(v, dict):
        label = str(v.get("label") or v.get("id") or v.get("spk") or v.get("speaker") or "")
        name  = v.get("name") or (label if label else None)
        return {"label": label or None, "name": name, "edited": bool(v.get("edited", False))}
    # 숫자/문자
    s = str(v).strip()
    if not s:
        return None
    name = s if not s.isdigit() else chr(ord('A') + (int(s)-1) % 26)  # "1" -> "A"
    return {"label": s, "name": name, "edited": False}

def _take_textlike(seg: Dict[str, Any]) -> str:
    return (seg.get("text") or seg.get("utterance") or seg.get("msg") or "").strip()

def _take_start(seg: Dict[str, Any]) -> float | None:
    return _normalize_time(seg.get("start") or seg.get("startTime") or seg.get("begin"))

def _take_end(seg: Dict[str, Any]) -> float | None:
    return _normalize_time(seg.get("end") or seg.get("endTime") or seg.get("finish"))



# === [보강] _parse_text ===================================================
def _parse_text(js: Any) -> str:
    """
    CLOVA 응답에서 전체 transcript(plain text)를 추출.
    js가 str(JSON)이어도 안전하게 처리.
    """
    js = _ensure_json(js)
    print("DEBUG _parse_text types:", type(js.get("result")), type(js.get("segments")))

    # 1) 최상위 text/fullText
    for key in ("fullText", "text"):
        t = js.get(key)
        if isinstance(t, str) and t.strip():
            return t.strip()

    # 2) result.* 계열
    res = js.get("result")
    if isinstance(res, dict):
        for key in ("fullText", "text"):
            t = res.get(key)
            if isinstance(t, str) and t.strip():
                return t.strip()

    # 3) segments에서 이어붙이기  ← ★여기를 안전하게 (res가 문자열일 수도 있음)
    segs = None
    if isinstance(res, dict):
        segs = res.get("segments")
    if not isinstance(segs, list):  # res가 dict가 아니거나 segments가 없으면 js 쪽 확인
        segs = js.get("segments")

    if isinstance(segs, list) and segs:
        lines = []
        for seg in segs:
            # 요소가 문자열인 경우 JSON 파싱 시도
            if isinstance(seg, str):
                try:
                    seg = json.loads(seg)
                except Exception:
                    continue
            if not isinstance(seg, dict):
                continue
            spk = seg.get("speaker") or seg.get("spk")
            spk_obj = _norm_speaker(spk)
            tag = f"[S{spk_obj['label']}]" if (spk_obj and spk_obj.get("label")) else ""
            txt = _take_textlike(seg)
            if txt:
                lines.append((f"{tag} " if tag else "") + txt)
        if lines:
            return "\n".join(lines)

    # 4) results[*].utterances or results[*].text 등  ← ★여기도 res 가드 필요
    results = js.get("results")
    if not isinstance(results, list) and isinstance(res, dict):
        results = res.get("results")

    if isinstance(results, list):
        lines = []
        for r in results:
            if isinstance(r, str):
                try:
                    r = json.loads(r)
                except Exception:
                    continue
            if not isinstance(r, dict):
                continue

            utts = r.get("utterances")
            if isinstance(utts, list):
                for u in utts:
                    if isinstance(u, str):
                        try:
                            u = json.loads(u)
                        except Exception:
                            continue
                    if not isinstance(u, dict):
                        continue
                    spk_obj = _norm_speaker(u.get("speaker") or u.get("spk"))
                    tag = f"[S{spk_obj['label']}]" if (spk_obj and spk_obj.get("label")) else ""
                    txt = _take_textlike(u)
                    if txt:
                        lines.append((f"{tag} " if tag else "") + txt)

            t = r.get("text")
            if isinstance(t, str) and t.strip():
                lines.append(t.strip())

        if lines:
            return "\n".join(lines)

    # 마지막 폴백: 원문 JSON
    return json.dumps(js, ensure_ascii=False)

def _normalize_time(v):
    if v is None: return None
    v = float(v)
    return v/1000.0 if v > 1e3 else v

# === [보강] _extract_segments =============================================
def _extract_segments(obj: Any) -> List[Dict[str, Any]]:
    obj = _ensure_json(obj)
    res = obj.get("result") if isinstance(obj.get("result"), dict) else obj

    # 후보 리스트들을 순서대로 탐색
    candidates: List[Optional[List[Any]]] = [
        res.get("segments") if isinstance(res.get("segments"), list) else None,
        obj.get("segments") if isinstance(obj.get("segments"), list) else None,
        # diarization.segments
        (res.get("diarization") or {}).get("segments") if isinstance((res.get("diarization") or {}).get("segments"), list) else None,
        # results[*].utterances
        sum(
            [
                (r if isinstance(r, dict) else _ensure_json(r) or {}).get("utterances") or []
                for r in (res.get("results") or obj.get("results") or [])
            ],
            []
        ) or None,
    ]

    raw = next((c for c in candidates if c), None)
    if not raw:
        return []

    out: List[Dict[str, Any]] = []
    for i, s in enumerate(raw, 1):
        if isinstance(s, str):
            try:
                s = json.loads(s)
            except Exception:
                continue
        if not isinstance(s, dict):
            continue

        spk_obj = _norm_speaker(s.get("speaker") or s.get("spk"))
        out.append({
            "idx": i,
            "speaker": spk_obj,  # {"label","name","edited"} | None
            "start": _take_start(s),
            "end": _take_end(s),
            "text": _take_textlike(s),
        })

    # 타임스탬프 보정
    for i, seg in enumerate(out):
        if seg["start"] is None and i > 0:
            seg["start"] = out[i-1]["end"]
        if seg["end"] is None and i+1 < len(out):
            seg["end"] = out[i+1]["start"]
        if seg["start"] is not None and seg["end"] is not None and seg["end"] < seg["start"]:
            seg["end"] = seg["start"]
    return out

# === [신규] 세그먼트 폴백(segments 비거나 모두 text 빈 경우) ================
def _segments_fallback_from_text(text: str, approx_sec: int = 40) -> List[Dict[str, Any]]:
    """
    타임라인 정보가 없을 때 텍스트를 N글자/문장 단위로 잘라
    start/end 없이 스피커 미정 블록을 만든다. (클라이언트에서 편집/수정 전제)
    """
    if not text or not text.strip():
        return []
    # 문장 단위로 대충 쪼개기
    chunks = re.split(r'(?<=[.!?。！？\n])\s+', text.strip())
    chunks = [c.strip() for c in chunks if c.strip()]
    out: List[Dict[str, Any]] = []
    for i, c in enumerate(chunks, 1):
        out.append({
            "idx": i,
            "speaker": None,
            "start": None,
            "end": None,
            "text": c,
        })
    return out
def _post_upload(file_path: str, completion: str) -> dict:
    if not BASE_URL or not SECRET:
        raise RuntimeError("CLOVA_SPEECH_INVOKE_URL / CLOVA_SPEECH_API_KEY 환경변수를 설정하세요.")
    url = f"{BASE_URL}/recognizer/upload"
    headers = {"Accept": "application/json;UTF-8", "X-CLOVASPEECH-API-KEY": SECRET}
    params = {
        "language": LANG,
        "completion": completion,
        "diarization": {"enable": True},
        "wordAlignment": True,
        "fullText": True,
    }
    with open(file_path, "rb") as f:
        files = [
            ("media", (os.path.basename(file_path), f, "application/octet-stream")),
            ("params", (None, json.dumps(params, ensure_ascii=False).encode("UTF-8"), "application/json")),
        ]
        resp = requests.post(url, headers=headers, files=files, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise Exception(f"Clova Upload {resp.status_code}: {resp.text}")
    return resp.json()


def transcribe_audio(file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
    js = _post_upload(file_path, completion="sync")  # sync 유지
    js = _ensure_json(js)

    text = _parse_text(js)
    segments = _extract_segments(js)

    # 세그먼트가 없거나 모두 빈 텍스트인 경우 폴백
    if not segments or all(not (s.get("text") or "").strip() for s in segments):
        fb = _segments_fallback_from_text(text)
        if fb:
            segments = fb
    return text, segments

def _ensure_json(obj):
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, str):
        try:
            return json.loads(obj)
        except Exception:
            return {"text": obj}
    return {"text": str(obj)}


def transcribe_audio(file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
    js = _post_upload(file_path, completion="sync")  # sync 유지
    js = _ensure_json(js)

    text = _parse_text(js)
    segments = _extract_segments(js)

    # 세그먼트가 없거나 모두 빈 텍스트인 경우 폴백
    if not segments or all(not (s.get("text") or "").strip() for s in segments if isinstance(s, dict)):
        fb = _segments_fallback_from_text(text)
        if fb:
            segments = fb

    # ✅ 최종 타입 보장
    if not isinstance(text, str):
        text = str(text or "")
    if not isinstance(segments, list):
        segments = []
    else:
        # list 안에 dict 아닌 항목이 섞였을 가능성 제거
        segments = [s for s in segments if isinstance(s, dict)]

    return text, segments

