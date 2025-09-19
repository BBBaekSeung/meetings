# apps/api/llm_service.py

import re
import os
import json
from typing import Any, Dict, List, Optional
import google.generativeai as genai
from datetime import date as _date

def _today_ymd() -> str:
    return _date.today().isoformat()



# ─────────────────────────────────────────────────────────────
# Gemini 설정
# ─────────────────────────────────────────────────────────────
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    print(f"Gemini API 키 설정에 실패했습니다: {e}")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# ─────────────────────────────────────────────────────────────
# 헬퍼: 마크다운 코드펜스 제거 / 마지막 JSON 블록 추출
# ─────────────────────────────────────────────────────────────
def _strip_md_fences(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()

def _extract_last_json_block(s: str) -> str:
    """
    응답에 잡음이 섞여도 마지막 JSON 객체만 잡아 파싱한다.
    중첩 괄호를 스택으로 추적.
    """
    s = s or ""
    stack = []
    start = -1
    last = None
    for i, ch in enumerate(s):
        if ch == '{':
            if not stack:
                start = i
            stack.append('{')
        elif ch == '}':
            if stack:
                stack.pop()
                if not stack and start != -1:
                    last = s[start:i+1]
    return last if last is not None else s


# ─────────────────────────────────────────────────────────────
# 헬퍼: 최대 3문장 요약
# ─────────────────────────────────────────────────────────────
def _sentences3(text: str) -> List[str]:
    """
    한글 문장부호(., !, ?, 。, ！, ？)와 '다' 종결을 기준으로 최대 3문장.
    """
    if not text:
        return ["요약 없음"]
    s = text.strip()

    # 1) 표준 문장부호 기준 분리
    parts = re.split(r'(?<=[\.!?。！？])\s+|\n+', s)

    # 2) 여전히 길게 붙은 구간에서 '다' 종결 기준 추가 분리
    split2 = []
    for p in parts:
        # '다 ' 뒤 공백 지점에서 분리 (고정 폭 룩어헤드/룩비하인드 조합)
        segs = re.split(r'(?<=다)\s+(?=[A-Z가-힣0-9\"\'])', p)
        split2.extend(segs)

    cleaned = [re.sub(r'\s+', ' ', x).strip() for x in split2 if x and x.strip()]
    return cleaned[:3] if cleaned else ["요약 없음"]


# ─────────────────────────────────────────────────────────────
# 헬퍼: 타입 보정/정규화
# ─────────────────────────────────────────────────────────────
def _coerce_top_obj(maybe: Any) -> Optional[Dict[str, Any]]:
    """최상위가 dict가 아니면 None."""
    return maybe if isinstance(maybe, dict) else None

def _to_list(value: Any) -> List[Any]:
    """리스트 아닌 경우 안전하게 빈 리스트로."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []

def _safe_get(d: Any, key: str, default=None):
    return d.get(key, default) if isinstance(d, dict) else default


# ─────────────────────────────────────────────────────────────
# 메인 함수
# ─────────────────────────────────────────────────────────────
def summarize_and_extract(transcript: str) -> dict:
    """
    transcript 인자로 '원문 문자열' 또는
    {"transcript": str, "segments": [{idx, speaker:{label,name}, text, ...}, ...]} 형태의
    JSON 문자열이 들어와도 처리합니다.

    반환 형태(우리 API와 호환):
    {
      "summary": [ "문장1", "문장2", "문장3" ],
      "actions": [
        { "title": str, "owner": str|None, "due": "YYYY-MM-DD"|None, "note": None, "status": "todo", "start_date": _today_ymd() }
      ]
    }
    """
    # 1) 입력 파싱 (원문/JSON 모두 허용)
    raw_txt = transcript or ""
    segs = None
    flat_text = raw_txt
    try:
        maybe = json.loads(raw_txt)
        if isinstance(maybe, dict):
            flat_text = _safe_get(maybe, "transcript", "") or ""
            segs = _safe_get(maybe, "segments", None)
    except Exception:
        pass  # 평문이면 그대로 진행

    # 2) LLM 입력 페이로드 구성
    payload = {
        "transcript": (flat_text or "").strip(),
        "segments": segs if isinstance(segs, list) else None,
    }

    # 3) 프롬프트
    prompt = f"""
너는 한국어 회의록을 구조화하는 '회의록 전문가'다. 아래 입력을 읽고 **반드시 유효한 JSON 객체만** 반환하라.
마크다운 코드펜스(````), 설명, 여분 텍스트는 절대 출력하지 마라.

[INPUT - JSON]
{json.dumps(payload, ensure_ascii=False)}

[지시사항]
- 입력은 transcript(전체 텍스트)와 segments(화자 분리 배열)로 구성될 수 있다.
- 사전 정리(출력 포함 금지): 전체 segments를 훑어 speaker.label → 실명/직책/팀명 매핑 테이블을 내부적으로 만든다. 소개 패턴(“저는 OOO입니다”, “OOO 팀장 OOO”)과 호칭(“OOO님”, “팀장님”)을 근거로 갱신한다.
- 담당자 추출 우선순위(텍스트 근거만):
1) 작업 문장에 명시된 실명/직책/팀명이 있으면 그 값을 사용.
2) 화자 1인칭(“제가/저/우리가 … 하겠습니다/맡겠습니다/처리합니다”)이면, 해당 speaker의 매핑된 실명/직책을 사용(없으면 label).
3) 화자 3인칭(“민수가/CS팀이 처리”)면 그 이름/팀을 사용.
4) 위가 불가하면 speaker.label을 사용.
5) 정말 배정 표현이 없을 때만 assignee=null로 둔다.
- 실행 가능한 작업만 action_items에 포함하고, 이미 끝났거나 추상적인 문구는 제외.
- 요약은 정보 위주 세 문단으로, 각 2~4문장, 마침표로 종결.
- 금지: 새로운 이름을 창작하거나 외부 지식을 사용하지 말 것.

[OUTPUT SCHEMA - keys must match exactly]
{{
  "summary": ["문단1","문단2","문단3"],
  "action_items": [
    {{ "task": "할 일", "assignee": "담당자|null", "due_date": "YYYY-MM-DD|null" }}
  ]
}}

[NEGATIVE EXAMPLES - never include as tasks]
- "논의함/검토함/공유함"처럼 이미 완료된 행위
- 추상적 선언("품질 개선 필요")
- 결정문(“가격 10% 인상 확정”)
- 정보요약/현상진단

[GOOD TASK EXAMPLES]
- "고객사 A에 견적안 송부"
- "결제 실패 로그 샘플 수집 및 분석 리포트 작성"
- "PoC 환경에서 v2.1 배포 및 성능 검증"

[FINAL INSTRUCTIONS]
- 출력은 오직 위 스키마의 **JSON 객체 한 개**.
- 키 추가/변경 금지, 값 누락 금지.
    """.strip()

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        raw = (response.text or "").strip()
        cleaned = _extract_last_json_block(_strip_md_fences(raw))
        data = json.loads(cleaned)

        # ✅ 최상위가 dict인지 강제 확인
        obj = _coerce_top_obj(data)
        if obj is None:
            raise ValueError(f"LLM JSON top-level is not an object: {type(data).__name__}")

        # ---- summary 정규화 ----
        summary_field = obj.get("summary")
        if isinstance(summary_field, str):
            summary = _sentences3(summary_field)
        elif isinstance(summary_field, list):
            summary = [re.sub(r'\s+', ' ', str(s)).strip() for s in summary_field if str(s).strip()]
            summary = summary[:3] if summary else ["요약 없음"]
        else:
            summary = ["요약 없음"]

        # ---- actions 정규화 ----
        raw_items = _to_list(obj.get("action_items"))
        actions: List[Dict[str, Any]] = []
        for it in raw_items:
            if not isinstance(it, dict):
                continue
            task = (it.get("task") or "").strip()
            if not task:
                continue
            assignee = it.get("assignee")
            assignee = assignee.strip() if isinstance(assignee, str) and assignee.strip() else None
            due = it.get("due_date")
            due = due.strip() if isinstance(due, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", due.strip()) else None

            actions.append({
                "title": task[:200],
                "owner": assignee,
                "due": due,
                "note": None,
                "status": "todo",
                "start_date": _today_ymd(),
            })

        return {"summary": summary, "actions": actions}
    
    except Exception as e:
        print(f"Gemini LLM Error: {e}")
        base = payload.get("transcript") or ""
        if not base and payload.get("segments"):
            try:
                seg_lines = []
                for s in payload["segments"]:
                    if not isinstance(s, dict):
                        # 문자열/기타 타입이면 스킵
                        continue
                    sp = s.get("speaker") or {}
                    if not isinstance(sp, dict):
                        sp = {}
                    name = (sp.get("name") or sp.get("label") or "").strip()
                    text = (s.get("text") or "").strip()
                    line = f"{name}: {text}".strip(": ").strip()
                    if line:
                        seg_lines.append(line)
                base = " ".join(seg_lines)
            except Exception:
                # 어떤 예외가 나더라도 폴백은 그대로 진행
                pass

        return {
            "summary": _sentences3(base or ""),
            "actions": []
        }
