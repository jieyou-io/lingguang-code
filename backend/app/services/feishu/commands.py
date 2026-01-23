"""
Feishu bot command parsing and handlers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from app.core.config import settings
from app.services.project_manager import ProjectManagerService
from app.api.routers import models as model_router


ENGINE_LIST = ["claude", "codex", "gemini"]


@dataclass
class CommandAction:
    kind: str  # reply | help | engine | card_projects
    text: Optional[str] = None
    prompt: Optional[str] = None
    data: Optional[dict] = None


def _split_args(text: str) -> List[str]:
    return [part for part in text.strip().split() if part]


async def _get_default_model(engine: str) -> Optional[str]:
    models = await model_router.get_engine_models(engine)
    for model in models:
        if model.is_default:
            return model.id
    if models:
        return models[0].id
    if engine == "claude":
        return settings.FEISHU_DEFAULT_MODEL
    return None


async def _list_models(engine: str) -> str:
    models = await model_router.get_engine_models(engine)
    if not models:
        return "未找到可用模型。"
    lines = ["可用模型:"]
    for item in models:
        suffix = " (default)" if item.is_default else ""
        lines.append(f"- {item.id}{suffix}")
    return "\n".join(lines)


async def _list_engine_commands(engine: str, project_path: Optional[str]) -> str:
    commands = await model_router.get_engine_slash_commands(engine, project_path)
    if not commands:
        return "未找到可用命令。"
    lines = ["可用命令:"]
    for cmd in commands:
        lines.append(f"- /{cmd.name} ({cmd.category})")
    return "\n".join(lines)


def _context_summary(context: Dict[str, Optional[str]]) -> str:
    engine = context.get("engine") or settings.FEISHU_DEFAULT_ENGINE
    model = context.get("model") or settings.FEISHU_DEFAULT_MODEL
    project_path = context.get("project_path") or "未选择"
    session_id = context.get("session_id") or "未选择"
    return (
        f"engine: {engine}\n"
        f"model: {model}\n"
        f"project: {project_path}\n"
        f"session: {session_id}"
    )


async def handle_command(
    text: str,
    context: Dict[str, Optional[str]],
) -> Optional[CommandAction]:
    if not text.startswith("/"):
        return None

    parts = _split_args(text)
    if not parts:
        return CommandAction(kind="reply", text="无效命令。")

    command = parts[0].lower()
    args = parts[1:]

    if command.startswith("/cli-"):
        prompt = "/" + command[len("/cli-"):]
        if args:
            prompt = f"{prompt} {' '.join(args)}"
        return CommandAction(kind="engine", prompt=prompt)

    if command == "/engine":
        if not args:
            return CommandAction(kind="reply", text=_context_summary(context))
        if args[0] == "list":
            return CommandAction(kind="reply", text="可用引擎: " + ", ".join(ENGINE_LIST))
        if args[0] == "set" and len(args) >= 2:
            engine = args[1].lower()
            if engine not in ENGINE_LIST:
                return CommandAction(kind="reply", text="引擎无效，可用: " + ", ".join(ENGINE_LIST))
            context["engine"] = engine
            context["model"] = await _get_default_model(engine)
            return CommandAction(kind="reply", text=f"引擎已切换为 {engine}")
        return CommandAction(kind="reply", text="用法: /engine | /engine list | /engine set <engine>")

    if command == "/model":
        engine = context.get("engine") or settings.FEISHU_DEFAULT_ENGINE
        if not args:
            current = context.get("model") or settings.FEISHU_DEFAULT_MODEL
            return CommandAction(kind="reply", text=f"当前模型: {current}")
        if args[0] == "list":
            return CommandAction(kind="reply", text=await _list_models(engine))
        if args[0] == "set" and len(args) >= 2:
            model_id = args[1]
            context["model"] = model_id
            return CommandAction(kind="reply", text=f"模型已切换为 {model_id}")
        return CommandAction(kind="reply", text="用法: /model | /model list | /model set <model>")

    if command == "/projects":
        service = ProjectManagerService()
        projects = await service.list_integrated_projects()
        if not projects:
            return CommandAction(kind="reply", text="未找到项目。")
        return CommandAction(kind="card_projects", data={"projects": projects, "page": 1})

    if command == "/dialogs":
        if not args:
            return CommandAction(kind="reply", text="用法: /dialogs <projectId>")
        project_id = args[0]
        service = ProjectManagerService()
        sessions = service.get_project_sessions(project_id)
        if not sessions:
            return CommandAction(kind="reply", text="未找到会话。")
        context["project_id"] = project_id
        context["project_path"] = sessions[0].get("project_path") if sessions else None
        lines = ["会话列表:"]
        for item in sessions:
            session_id = item.get("id")
            first_message = item.get("first_message") or ""
            lines.append(f"- {session_id} | {first_message[:60]}")
        return CommandAction(kind="reply", text="\n".join(lines))

    if command == "/choice":
        if not args:
            return CommandAction(kind="reply", text="用法: /choice <sessionId>")
        if not context.get("project_id"):
            return CommandAction(kind="reply", text="请先使用 /dialogs 选择项目。")
        session_id = args[0]
        service = ProjectManagerService()
        sessions = service.get_project_sessions(context["project_id"])
        matched = next((s for s in sessions if s.get("id") == session_id), None)
        if not matched:
            return CommandAction(kind="reply", text="未找到该会话。")
        context["session_id"] = session_id
        context["engine"] = matched.get("engine") or context.get("engine")
        context["model"] = matched.get("model") or context.get("model")
        context["project_path"] = matched.get("project_path") or context.get("project_path")
        return CommandAction(kind="reply", text=f"已选择会话 {session_id}")

    if command == "/new":
        context["session_id"] = None
        if not context.get("engine"):
            context["engine"] = settings.FEISHU_DEFAULT_ENGINE
        if not context.get("model"):
            context["model"] = settings.FEISHU_DEFAULT_MODEL
        return CommandAction(kind="reply", text="已创建新会话。")

    if command == "/help":
        if args:
            target = args[0].lower()
            detail_map = {
                "/engine": "/engine | /engine list | /engine set <engine>",
                "/model": "/model | /model list | /model set <model>",
                "/projects": "/projects",
                "/dialogs": "/dialogs <projectId>",
                "/choice": "/choice <sessionId>",
                "/new": "/new",
                "/cli-": "/cli-<command> [args...]",
                "/cli-list": "/cli-list <engine>",
                "/true": "/true (群聊开启 @bot 触发)",
                "/false": "/false (群聊关闭 @bot 触发，需要 @bot)",
            }
            key = target if target.startswith("/") else f"/{target}"
            detail = detail_map.get(key)
            if detail:
                return CommandAction(kind="help", data={"title": "命令帮助", "lines": [detail]})
            return CommandAction(kind="help", data={"title": "命令帮助", "lines": ["未知命令。使用 /help 查看列表。"]})
        return CommandAction(
            kind="help",
            data={
                "title": "命令列表",
                "lines": [
                    "/engine  查看当前引擎",
                    "/engine list  列出可用引擎",
                    "/engine set <engine>  切换引擎",
                    "/model  查看当前模型",
                    "/model list  列出当前引擎可用模型",
                    "/model set <model>  切换模型",
                    "/projects  列出项目路径",
                    "/dialogs <projectId>  查看项目会话列表",
                    "/choice <sessionId>  选择会话",
                    "/new  新建会话",
                    "/cli-<command> [args...]  透传引擎命令",
                    "/cli-list <engine>  列出引擎命令",
                    "/true  群聊开启 @bot 触发",
                    "/false  群聊关闭 @bot 触发(需@bot)",
                    "/help [cmd]  查看帮助",
                ],
            },
        )

    if command == "/cli-list":
        if not args:
            return CommandAction(kind="reply", text="用法: /cli-list <engine>")
        engine = args[0].lower()
        if engine not in ENGINE_LIST:
            return CommandAction(kind="reply", text="引擎无效，可用: " + ", ".join(ENGINE_LIST))
        project_path = context.get("project_path")
        return CommandAction(kind="reply", text=await _list_engine_commands(engine, project_path))

    return CommandAction(kind="reply", text="未知命令。使用 /help 查看。")
