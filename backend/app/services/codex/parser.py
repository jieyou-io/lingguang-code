"""
Codex 响应解析器
"""
import json
from typing import Any, Dict, Optional, Tuple


def parse_json_line(line: str) -> Dict[str, Any]:
    """解析 JSON 行"""
    text = line.strip()
    if not text:
        raise ValueError("empty line")
    return json.loads(text)


def safe_parse_json_line(line: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """安全解析 JSON 行"""
    try:
        return parse_json_line(line), None
    except (ValueError, json.JSONDecodeError) as exc:
        return None, str(exc)
