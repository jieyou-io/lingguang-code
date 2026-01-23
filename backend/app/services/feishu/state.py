"""
Feishu bot state storage (persistent).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from filelock import FileLock


@dataclass
class FeishuContext:
    context_id: str
    chat_id: str
    thread_id: str
    user_id: str
    project_id: Optional[str] = None
    project_path: Optional[str] = None
    session_id: Optional[str] = None
    engine: Optional[str] = None
    model: Optional[str] = None


class FeishuStateStore:
    def __init__(self, path: str) -> None:
        self._path = Path(path).expanduser()
        self._lock = FileLock(str(self._path) + ".lock")

    def load(self) -> Dict[str, Any]:
        if not self._path.exists():
            return {"chats": {}, "contexts": {}}
        try:
            with self._lock:
                raw = self._path.read_text(encoding="utf-8")
            return json.loads(raw) if raw else {"chats": {}, "contexts": {}}
        except (OSError, json.JSONDecodeError):
            return {"chats": {}, "contexts": {}}

    def save(self, data: Dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        with self._lock:
            self._path.write_text(payload, encoding="utf-8")

    def get_chat_config(self, chat_id: str) -> Dict[str, Any]:
        data = self.load()
        return data.get("chats", {}).get(chat_id, {})

    def set_chat_config(self, chat_id: str, config: Dict[str, Any]) -> None:
        data = self.load()
        chats = data.setdefault("chats", {})
        chats[chat_id] = config
        self.save(data)

    def get_context(self, context_id: str) -> Dict[str, Any]:
        data = self.load()
        return data.get("contexts", {}).get(context_id, {})

    def set_context(self, context_id: str, context: Dict[str, Any]) -> None:
        data = self.load()
        contexts = data.setdefault("contexts", {})
        contexts[context_id] = context
        self.save(data)
