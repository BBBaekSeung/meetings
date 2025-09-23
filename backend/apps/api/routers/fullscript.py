from typing import List, Dict, Any, Tuple
import json

def normalize_segments(raw_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """다양한 STT 세그먼트 포맷을 내부 통일 포맷으로 정규화."""
    out = []
    for s in raw_segments:
        # 지원 포맷 A: {"speaker": {"label": "3", "name": "C", ...}}
        spk_obj = s.get("speaker")
        if isinstance(spk_obj, dict):
            spk_key = spk_obj.get("name") or spk_obj.get("label") or "unknown"
        else:
            # 지원 포맷 B: {"speaker": "spk_0"}
            spk_key = s.get("speaker") or "unknown"

        out.append({
            "idx": s.get("idx"),
            "speaker_key": str(spk_key),
            "text": s.get("text", "").strip(),
        })
    # idx가 있으면 idx 기준 정렬, 없으면 주어진 순서 유지
    out.sort(key=lambda x: x["idx"] if x["idx"] is not None else 10**12)
    return out

def build_speaker_map(norm_segments: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    등장 순서대로 참가자1, 참가자2… 부여.
    동일 speaker_key는 동일한 참가자 번호를 유지.
    """
    m: Dict[str, str] = {}
    counter = 1
    for s in norm_segments:
        k = s["speaker_key"]
        if k not in m:
            m[k] = f"참가자{counter}"
            counter += 1
    return m

def merge_consecutive(norm_segments: List[Dict[str, Any]]) -> List[Tuple[str,str]]:
    """
    같은 화자의 연속 세그먼트를 한 줄로 합치기.
    returns: [(display_name, merged_text), ...]
    """
    if not norm_segments:
        return []
    spk_map = build_speaker_map(norm_segments)
    merged: List[Tuple[str,str]] = []
    cur_spk = None
    cur_text = []
    for s in norm_segments:
        disp = spk_map[s["speaker_key"]]
        if cur_spk is None:
            cur_spk = disp
            cur_text = [s["text"]]
        elif disp == cur_spk:
            cur_text.append(s["text"])
        else:
            merged.append((cur_spk, " ".join(t for t in cur_text if t)))
            cur_spk = disp
            cur_text = [s["text"]]
    # flush
    merged.append((cur_spk, " ".join(t for t in cur_text if t)))
    return merged

def to_lines(norm_segments: List[Dict[str, Any]], merge: bool) -> List[str]:
    """
    텍스트 라인 배열로 변환. merge=True면 연속 병합, False면 세그먼트 단위.
    """
    spk_map = build_speaker_map(norm_segments)
    if merge:
        pairs = merge_consecutive(norm_segments)
        return [f"{disp}: {txt}".strip() for disp, txt in pairs if txt]
    else:
        lines = []
        for s in norm_segments:
            disp = spk_map[s["speaker_key"]]
            txt = s["text"]
            if txt:
                lines.append(f"{disp}: {txt}")
        return lines
