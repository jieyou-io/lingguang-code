"""
Gemini 输出解析器
"""
import json
from typing import Any, Dict, Optional, Tuple


def parse_jsonl_line(line: bytes) -> Dict[str, Any]:
    """解析 JSONL 单行"""
    text = line.decode("utf-8").strip()
    if not text:
        raise ValueError("empty line")
    return json.loads(text)


def safe_parse_jsonl_line(line: bytes) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """安全解析 JSONL 单行"""
    try:
        return parse_jsonl_line(line), None
    except (ValueError, json.JSONDecodeError) as exc:
        return None, str(exc)
