# apps/api/task_classifier.py
import re
from typing import Literal

TaskType = Literal["일반", "체크리스트", "데이터 취합", "투표"]

KW = {
    "투표": [
        r"투표", r"찬반", r"과반", r"득표", r"\bpoll\b", r"설문\s*(참여|선택|응답)"
    ],
    "데이터 취합": [
        r"제출", r"취합", r"수집", r"모아서", r"모으",
        r"(구글)?폼", r"엑셀", r"스프레드시트",
        r"입력해", r"자료\s*(요청|받|보내)"
    ],
    "체크리스트": [
        r"체크\s*리스트", r"체크", r"점검", r"확인(?:해|하)", r"리스트", r"항목별", r"완료표시", r"\bqa\b"
    ],
}
PRIORITY = ["투표", "데이터 취합", "체크리스트"]  # 충돌 시 우선순위

def classify_task_type(text: str) -> TaskType:
    s = (text or "").lower()
    hits = set()
    for label, patterns in KW.items():
        for pat in patterns:
            if re.search(pat, s):   # 그대로 OK (아래 보완 팁 참고)
                hits.add(label); break
    for label in PRIORITY:
        if label in hits:
            return label
    # 기존: return "체크리스트" if "체크" in s else "일반"
    return "일반"
