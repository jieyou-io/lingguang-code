"""
Feishu interactive card builders.
"""
from __future__ import annotations

from typing import List, Dict, Optional


def _truncate(text: str, limit: int = 80) -> str:
    if len(text) <= limit:
        return text
    return text[:limit - 1] + "…"


def build_projects_card(projects: List[Dict], page: int, page_size: int = 10) -> Dict:
    total = len(projects)
    start = max(page - 1, 0) * page_size
    end = start + page_size
    page_items = projects[start:end]

    elements = []
    for item in page_items:
        path = item.get("path", "")
        project_id = item.get("id", "")
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": _truncate(path, 90), "text_align": "left"},
                        "type": "primary",
                        "value": {
                            "action": "select_project",
                            "project_id": project_id,
                            "project_path": path,
                        },
                    }
                ],
            }
        )

    nav_actions = []
    if page > 1:
        nav_actions.append(
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "上一页"},
                "value": {"action": "projects_page", "page": page - 1},
            }
        )
    if end < total:
        nav_actions.append(
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "下一页"},
                "value": {"action": "projects_page", "page": page + 1},
            }
        )
    if nav_actions:
        elements.append({"tag": "action", "actions": nav_actions})

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": f"项目列表 (第 {page} 页)"},
        },
        "elements": elements,
    }


def build_sessions_card(
    project_id: str,
    project_path: str,
    sessions: List[Dict],
    page: int,
    page_size: int = 10,
) -> Dict:
    total = len(sessions)
    start = max(page - 1, 0) * page_size
    end = start + page_size
    page_items = sessions[start:end]

    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "plain_text",
                "content": f"项目: {project_path}",
            },
        }
    ]

    for item in page_items:
        session_id = item.get("id", "")
        first_message = item.get("first_message") or ""
        engine = (item.get("engine") or "").lower()
        engine_label = _engine_label(engine)
        content = _truncate(first_message.replace("\n", " "), 90)
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": f"{engine_label} {content or session_id}".strip(),
                            "text_align": "left",
                        },
                        "value": {
                            "action": "select_session",
                            "project_id": project_id,
                            "session_id": session_id,
                            "project_path": project_path,
                        },
                    }
                ],
            }
        )

    # New session button
    elements.append(
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "新建会话"},
                    "type": "primary",
                    "value": {
                        "action": "new_session",
                        "project_id": project_id,
                        "project_path": project_path,
                    },
                }
            ],
        }
    )

    nav_actions = []
    if page > 1:
        nav_actions.append(
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "上一页"},
                "value": {
                    "action": "sessions_page",
                    "project_id": project_id,
                    "project_path": project_path,
                    "page": page - 1,
                },
            }
        )
    if end < total:
        nav_actions.append(
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "下一页"},
                "value": {
                    "action": "sessions_page",
                    "project_id": project_id,
                    "project_path": project_path,
                    "page": page + 1,
                },
            }
        )
    if nav_actions:
        elements.append({"tag": "action", "actions": nav_actions})

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "green",
            "title": {"tag": "plain_text", "content": f"会话列表 (第 {page} 页)"},
        },
        "elements": elements,
    }


def _engine_label(engine: str) -> str:
    if engine == "claude":
        return "[Claude]"
    if engine == "codex":
        return "[Codex]"
    if engine == "gemini":
        return "[Gemini]"
    return "[Unknown]"
