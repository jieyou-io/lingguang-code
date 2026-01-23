"""
Feishu bot integration using long connection SDK.
"""
from __future__ import annotations

import asyncio
import json
import re
import threading
import os
from typing import Any, Dict, Optional

import structlog

try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import (
        CreateMessageRequest,
        CreateMessageRequestBody,
    )
    from lark_oapi.api.im.v1.model.create_pin_request import CreatePinRequest
    from lark_oapi.api.im.v1.model.create_pin_request_body import CreatePinRequestBody
    from lark_oapi.api.im.v1.model.get_chat_announcement_request import GetChatAnnouncementRequest
    from lark_oapi.api.im.v1.model.patch_chat_announcement_request import PatchChatAnnouncementRequest
    from lark_oapi.api.im.v1.model.patch_chat_announcement_request_body import (
        PatchChatAnnouncementRequestBody,
    )
    from lark_oapi.event.callback.model.p2_card_action_trigger import (
        P2CardActionTriggerResponse,
    )
except Exception:  # pragma: no cover - optional dependency
    lark = None

from app.core.config import settings
from app.services.feishu.commands import CommandAction, handle_command
from app.services.feishu.cards import build_projects_card, build_sessions_card
from app.services.feishu.state import FeishuStateStore
from app.services.project_manager import ProjectManagerService
from app.services.storage.repositories import StorageRepository
from app.services.claude.service import ClaudeService, claude_registry, _shared_runner
from app.services.codex.service import CodexService, codex_registry
from app.services.codex.runner import CodexRunner
from app.services.gemini.service import GeminiService, gemini_registry
from app.services.gemini.runner import GeminiRunner
from app.core.sse import SSEEventType


logger = structlog.get_logger()


def _safe_get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"<at [^>]+>.*?</at>", "", text)
    return cleaned.strip()


def _normalize_command(text: str) -> str:
    normalized = text.replace("／", "/").strip()
    if not normalized:
        return normalized
    if normalized.startswith("/"):
        return normalized
    idx = normalized.find("/")
    if idx == -1:
        return normalized
    if idx == 0 or normalized[idx - 1].isspace():
        return normalized[idx:].strip()
    return normalized


def _build_context_id(chat_id: str, thread_id: str, chat_type: str) -> str:
    if chat_type == "p2p":
        return f"p2p:{chat_id}"
    if thread_id:
        return f"{chat_id}:{thread_id}"
    return chat_id


class FeishuBot:
    def __init__(self) -> None:
        self._store = FeishuStateStore(settings.FEISHU_STATE_PATH)
        self._client = None
        self._ws_client = None
        self._thread = None

    def start(self) -> None:
        if not settings.FEISHU_ENABLE:
            logger.info("feishu_bot_disabled")
            return
        if lark is None:
            logger.warning("feishu_sdk_not_installed")
            return
        if not settings.FEISHU_APP_ID or not settings.FEISHU_APP_SECRET:
            logger.warning("feishu_config_missing")
            return

        self._client = lark.Client.builder().app_id(settings.FEISHU_APP_ID).app_secret(
            settings.FEISHU_APP_SECRET
        ).build()

        handler_builder = lark.EventDispatcherHandler.builder(
            settings.FEISHU_APP_ID,
            settings.FEISHU_APP_SECRET,
        )
        handler_builder.register_p2_im_message_receive_v1(self._on_message)
        handler_builder.register_p2_card_action_trigger(self._on_card_action)
        handler = handler_builder.build()

        if self._thread and self._thread.is_alive():
            logger.info("feishu_bot_already_running")
            return

        self._thread = threading.Thread(
            target=self._run_ws_client,
            args=(handler,),
            daemon=True,
        )
        self._thread.start()
        logger.info("feishu_bot_started")

    def stop(self) -> None:
        if self._ws_client and hasattr(self._ws_client, "stop"):
            try:
                self._ws_client.stop()
            except Exception:
                logger.warning("feishu_bot_stop_failed")

    def _on_message(self, data: Any) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._handle_message(data))
            return
        loop.create_task(self._handle_message(data))

    def _on_card_action(self, data: Any):
        if lark is None:
            return None
        try:
            logger.info("feishu_card_action_received")
            def worker():
                try:
                    asyncio.run(self._handle_card_action(data))
                except Exception as exc:
                    logger.error("feishu_card_action_worker_failed", error=str(exc))

            threading.Thread(target=worker, daemon=True).start()
            return P2CardActionTriggerResponse()
        except Exception as exc:
            logger.error("feishu_card_action_handler_failed", error=str(exc))
            return P2CardActionTriggerResponse()

    def _run_ws_client(self, handler: Any) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            import lark_oapi.ws.client as lark_ws_client
            lark_ws_client.loop = loop
        except Exception:
            pass
        self._ws_client = lark.ws.Client(
            settings.FEISHU_APP_ID,
            settings.FEISHU_APP_SECRET,
            event_handler=handler,
            log_level=lark.LogLevel.INFO,
        )
        try:
            self._ws_client.start()
        finally:
            loop.stop()
            loop.close()

    async def _handle_message(self, data: Any) -> None:
        if self._client is None:
            return

        event = _safe_get(data, "event")
        message = _safe_get(event, "message")
        sender = _safe_get(event, "sender")

        chat_id = _safe_get(message, "chat_id", "")
        chat_type = _safe_get(message, "chat_type", "group")
        message_id = _safe_get(message, "message_id", "")
        root_id = _safe_get(message, "root_id", "") or ""
        parent_id = _safe_get(message, "parent_id", "") or ""
        thread_id = root_id or parent_id

        sender_id = _safe_get(_safe_get(sender, "sender_id"), "open_id", "")
        if settings.FEISHU_BOT_OPEN_ID and sender_id == settings.FEISHU_BOT_OPEN_ID:
            return

        content_raw = _safe_get(message, "content", "") or ""
        msg_type = _safe_get(message, "message_type", "")
        if msg_type and msg_type != "text":
            await self._send_message(chat_id, "暂时只支持文本消息。", root_id=thread_id)
            return

        try:
            content_json = json.loads(content_raw)
            text = content_json.get("text", "")
        except json.JSONDecodeError:
            text = content_raw

        text = text.strip()
        if not text:
            return

        mentions = _safe_get(message, "mentions", []) or []
        mentioned = False
        for mention in mentions:
            name = _safe_get(mention, "name", "")
            mention_id = _safe_get(_safe_get(mention, "id"), "open_id", "")
            if settings.FEISHU_BOT_OPEN_ID and mention_id == settings.FEISHU_BOT_OPEN_ID:
                mentioned = True
                break
            if settings.FEISHU_BOT_NAME and name == settings.FEISHU_BOT_NAME:
                mentioned = True
                break

        cleaned_text = _normalize_text(text)
        command_text = _normalize_command(cleaned_text)
        context_id = _build_context_id(chat_id, thread_id, chat_type)
        logger.info(
            "feishu_message_received",
            chat_id=chat_id,
            chat_type=chat_type,
            thread_id=thread_id,
            sender_id=sender_id,
            message_id=message_id,
            text=cleaned_text,
            mentioned=mentioned,
        )

        chat_cfg = self._store.get_chat_config(chat_id)
        require_mention = chat_cfg.get("require_mention")
        if require_mention is None:
            require_mention = settings.FEISHU_REQUIRE_MENTION_DEFAULT

        if chat_type != "p2p":
            if command_text == "/true":
                self._store.set_chat_config(chat_id, {"require_mention": True})
                await self._send_message(chat_id, "已开启 @bot 触发。", root_id=thread_id)
                return
            if command_text == "/false":
                if not mentioned:
                    return
                self._store.set_chat_config(chat_id, {"require_mention": False})
                await self._send_message(chat_id, "已关闭 @bot 触发。", root_id=thread_id)
                return
            if require_mention and not mentioned:
                return

        context = self._store.get_context(context_id)
        if not context and thread_id:
            fallback_context_id = _build_context_id(chat_id, "", chat_type)
            context = self._store.get_context(fallback_context_id)
            if context:
                logger.info(
                    "feishu_context_fallback",
                    from_context=context_id,
                    to_context=fallback_context_id,
                )
        logger.info(
            "feishu_context_state",
            context_id=context_id,
            project_path=context.get("project_path") if context else None,
            session_id=context.get("session_id") if context else None,
            engine=context.get("engine") if context else None,
            model=context.get("model") if context else None,
        )
        if not context:
            context = {
                "project_id": None,
                "project_path": None,
                "session_id": None,
                "engine": settings.FEISHU_DEFAULT_ENGINE,
                "model": settings.FEISHU_DEFAULT_MODEL,
            }

        action = await handle_command(command_text, context)
        if action and action.kind == "reply":
            await self._send_message(chat_id, action.text or "", root_id=thread_id)
            self._store.set_context(context_id, context)
            return
        if action and action.kind == "help":
            data = action.data or {}
            title = data.get("title") or "帮助"
            lines = data.get("lines") or []
            await self._send_post_blocks(chat_id, title, lines, root_id=thread_id)
            return
        if action and action.kind == "card_projects":
            data = action.data or {}
            projects = data.get("projects", [])
            page = data.get("page", 1)
            card = build_projects_card(projects, page)
            await self._send_card(chat_id, card, root_id=thread_id)
            return
        if action and action.kind == "engine":
            prompt = action.prompt or ""
        else:
            prompt = cleaned_text

        if not context.get("project_path"):
            await self._send_message(chat_id, "请先选择项目：/projects", root_id=thread_id)
            self._store.set_context(context_id, context)
            return

        engine = context.get("engine") or settings.FEISHU_DEFAULT_ENGINE
        model = context.get("model") or settings.FEISHU_DEFAULT_MODEL

        response_text, session_id = await self._run_engine(
            engine=engine,
            project_path=context["project_path"],
            session_id=context.get("session_id"),
            prompt=prompt,
            model=model,
        )

        if session_id:
            context["session_id"] = session_id
        self._store.set_context(context_id, context)

        await self._send_message(chat_id, response_text or "无输出。", root_id=thread_id)

    async def _handle_card_action(self, payload: Any) -> None:
        event = _safe_get(payload, "event")
        token = _safe_get(event, "token")
        logger.info(
            "feishu_card_action_token",
            has_event=bool(event),
            token_present=bool(token),
            token_match=(token == settings.FEISHU_VERIFICATION_TOKEN) if settings.FEISHU_VERIFICATION_TOKEN else None,
            token_len=len(token) if isinstance(token, str) else 0,
        )
        # Card action token uses a different token than event callback token in long connection mode.

        try:
            action_data = _safe_get(_safe_get(event, "action"), "value") or {}
            action_name = action_data.get("action")
        except Exception as exc:
            logger.error("feishu_card_action_parse_failed", error=str(exc))
            return
        ctx = _safe_get(event, "context")
        chat_id = _safe_get(ctx, "open_chat_id", "") or ""
        # Card actions do not carry a real thread id. Use chat scope for consistency.
        thread_id = ""
        chat_type = _safe_get(event, "delivery_type", "group")
        sender_id = _safe_get(_safe_get(event, "operator"), "open_id", "")
        context_id = _build_context_id(chat_id, thread_id, chat_type)

        context = self._store.get_context(context_id)
        if not context:
            context = {
                "project_id": None,
                "project_path": None,
                "session_id": None,
                "engine": settings.FEISHU_DEFAULT_ENGINE,
                "model": settings.FEISHU_DEFAULT_MODEL,
            }

        logger.info(
            "feishu_card_action",
            action=action_name,
            chat_id=chat_id,
            thread_id=thread_id,
            sender_id=sender_id,
            action_data=action_data,
        )

        if action_name == "projects_page":
            page = int(action_data.get("page") or 1)
            service = ProjectManagerService()
            projects = await service.list_integrated_projects()
            card = build_projects_card(projects, page)
            await self._send_card(chat_id, card, root_id=thread_id)
            return

        if action_name == "select_project":
            project_id = action_data.get("project_id")
            project_path = action_data.get("project_path")
            if project_id and project_path:
                context["project_id"] = project_id
                context["project_path"] = project_path
                context["session_id"] = None
                self._store.set_context(context_id, context)
            service = ProjectManagerService()
            sessions = service.get_project_sessions(project_id)
            card = build_sessions_card(project_id, project_path, sessions, page=1)
            await self._send_card(chat_id, card, root_id=thread_id)
            return

        if action_name == "sessions_page":
            project_id = action_data.get("project_id") or context.get("project_id")
            project_path = action_data.get("project_path") or context.get("project_path") or ""
            page = int(action_data.get("page") or 1)
            if not project_id:
                await self._send_message(chat_id, "请先选择项目：/projects", root_id=thread_id)
                return
            service = ProjectManagerService()
            sessions = service.get_project_sessions(project_id)
            card = build_sessions_card(project_id, project_path, sessions, page=page)
            await self._send_card(chat_id, card, root_id=thread_id)
            return

        if action_name == "select_session":
            session_id = action_data.get("session_id")
            project_id = action_data.get("project_id") or context.get("project_id")
            project_path = action_data.get("project_path") or context.get("project_path")
            if not project_id or not session_id:
                await self._send_message(chat_id, "会话选择失败。", root_id=thread_id)
                return
            service = ProjectManagerService()
            sessions = service.get_project_sessions(project_id)
            matched = next((s for s in sessions if s.get("id") == session_id), None)
            if matched:
                context["session_id"] = session_id
                context["engine"] = matched.get("engine") or context.get("engine")
                context["model"] = matched.get("model") or context.get("model")
                context["project_path"] = project_path or matched.get("project_path")
                self._store.set_context(context_id, context)
                message_id = await self._send_text_notice(
                    chat_id,
                    "当前会话",
                    [
                        f"项目: {context.get('project_path') or '-'}",
                        f"会话: {session_id}",
                        f"引擎: {context.get('engine') or '-'}",
                        f"模型: {context.get('model') or '-'}",
                    ],
                    root_id=thread_id,
                )
                logger.info("feishu_session_notice_sent", message_id=message_id, chat_id=chat_id)
                await asyncio.sleep(0.3)
                await self._update_chat_announcement(
                    chat_id,
                    [
                        "当前会话",
                        f"项目: {context.get('project_path') or '-'}",
                        f"会话: {session_id}",
                        f"引擎: {context.get('engine') or '-'}",
                        f"模型: {context.get('model') or '-'}",
                    ],
                )
                await self._pin_message(message_id, chat_id=chat_id)
            else:
                await self._send_message(chat_id, "会话选择失败。", root_id=thread_id)
            return

        if action_name == "new_session":
            project_id = action_data.get("project_id") or context.get("project_id")
            project_path = action_data.get("project_path") or context.get("project_path")
            if project_id:
                context["project_id"] = project_id
            if project_path:
                context["project_path"] = project_path
            context["session_id"] = None
            self._store.set_context(context_id, context)
            message_id = await self._send_text_notice(
                chat_id,
                "当前会话",
                [
                    f"项目: {context.get('project_path') or '-'}",
                    "会话: 新建",
                    f"引擎: {context.get('engine') or '-'}",
                    f"模型: {context.get('model') or '-'}",
                ],
                root_id=thread_id,
            )
            logger.info("feishu_session_notice_sent", message_id=message_id, chat_id=chat_id)
            await asyncio.sleep(0.3)
            await self._update_chat_announcement(
                chat_id,
                [
                    "当前会话",
                    f"项目: {context.get('project_path') or '-'}",
                    "会话: 新建",
                    f"引擎: {context.get('engine') or '-'}",
                    f"模型: {context.get('model') or '-'}",
                ],
            )
            await self._pin_message(message_id, chat_id=chat_id)
            return

    async def _run_engine(
        self,
        engine: str,
        project_path: str,
        session_id: Optional[str],
        prompt: str,
        model: str,
    ) -> tuple[str, Optional[str]]:
        if engine == "claude":
            service = ClaudeService(StorageRepository(None), _shared_runner, claude_registry)
            from app.schemas.claude import ClaudeExecuteRequest, ClaudeResumeRequest

            if session_id:
                payload = ClaudeResumeRequest(
                    projectPath=project_path,
                    sessionId=session_id,
                    prompt=prompt,
                    model=model,
                )
                session_id = await service.resume(payload)
            else:
                payload = ClaudeExecuteRequest(
                    projectPath=project_path,
                    prompt=prompt,
                    model=model,
                )
                session_id = await service.execute(payload)
            text = await self._collect_stream(service.stream_events(session_id))
            return text, session_id

        if engine == "codex":
            service = CodexService(StorageRepository(None), CodexRunner(), codex_registry)
            from app.schemas.codex import CodexExecuteRequest

            payload = CodexExecuteRequest(
                projectPath=project_path,
                prompt=prompt,
                model=model,
                sessionId=session_id,
            )
            session_id = await service.execute(payload)
            text = await self._collect_stream(service.stream_events(session_id))
            return text, session_id

        if engine == "gemini":
            service = GeminiService(StorageRepository(None), GeminiRunner(), gemini_registry)
            from app.schemas.gemini import GeminiExecuteRequest

            payload = GeminiExecuteRequest(
                projectPath=project_path,
                prompt=prompt,
                model=model,
                sessionId=session_id,
            )
            session_id = await service.execute(payload)
            text = await self._collect_stream(service.stream_events(session_id))
            return text, session_id

        return "未支持的引擎。", session_id

    async def _collect_stream(self, stream: Any) -> str:
        chunks: list[str] = []
        async for event in stream:
            if event.type == SSEEventType.COMPLETE:
                break
            if event.type == SSEEventType.ERROR:
                error = ""
                if isinstance(event.payload, dict):
                    error = event.payload.get("error", "")
                if error:
                    chunks.append(f"[error] {error}")
            if event.type == SSEEventType.OUTPUT:
                text = self._extract_text(event.payload)
                if text:
                    chunks.append(text)
        return "".join(chunks).strip()

    def _extract_text(self, payload: Any) -> str:
        if not payload:
            return ""
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            if payload.get("type") == "message" and payload.get("role") == "user":
                return ""
            if payload.get("type") and isinstance(payload.get("item"), dict):
                item = payload.get("item", {})
                if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                    return item.get("text")
            content = payload.get("message", {}).get("content")
            if content is None:
                content = payload.get("content")
            if content is None and isinstance(payload.get("delta"), dict):
                content = payload.get("delta", {}).get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, str):
                        parts.append(item)
                    elif isinstance(item, dict):
                        if item.get("type") in ("text", "output_text", "input_text") and isinstance(item.get("text"), str):
                            parts.append(item.get("text"))
                return "".join(parts)
            if isinstance(payload.get("text"), str):
                return payload.get("text")
        return ""

    async def _send_message(self, chat_id: str, text: str, root_id: str = "") -> None:
        if not self._client:
            return
        if not text:
            return
        for chunk in self._chunk_text(text, 3500):
            if await self._send_post(chat_id, chunk, root_id):
                continue
            await self._send_plain_text(chat_id, chunk, root_id)

    async def _send_post(self, chat_id: str, text: str, root_id: str = "") -> bool:
        content = {
            "zh_cn": {
                "title": "",
                "content": [[{"tag": "text", "text": text}]],
            }
        }
        logger.info("feishu_post_payload", chat_id=chat_id, content=content)
        body_builder = (
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("post")
            .content(json.dumps(content, ensure_ascii=False))
        )
        self._set_thread_id(body_builder, root_id)
        req = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(body_builder.build())
            .build()
        )
        try:
            resp = self._client.im.v1.message.create(req)
            return getattr(resp, "success", lambda: False)()
        except Exception:
            return False

    async def _send_plain_text(self, chat_id: str, text: str, root_id: str = "") -> None:
        content = json.dumps({"text": text}, ensure_ascii=False)
        logger.info("feishu_text_payload", chat_id=chat_id, content={"text": text})
        body_builder = (
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("text")
            .content(content)
        )
        self._set_thread_id(body_builder, root_id)
        req = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(body_builder.build())
            .build()
        )
        self._client.im.v1.message.create(req)

    async def _send_card(self, chat_id: str, card: Dict[str, Any], root_id: str = "") -> None:
        if not self._client:
            return
        logger.info("feishu_send_card", chat_id=chat_id, root_id=root_id)
        body_builder = (
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("interactive")
            .content(json.dumps(card, ensure_ascii=False))
        )
        self._set_thread_id(body_builder, root_id)
        req = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(body_builder.build())
            .build()
        )
        self._client.im.v1.message.create(req)

    async def _send_post_blocks(self, chat_id: str, title: str, lines: list[str], root_id: str = "") -> Optional[str]:
        if not self._client:
            return None
        content_rows = []
        for line in lines:
            content_rows.append([{"tag": "text", "text": line}])
        payload = {"zh_cn": {"title": title, "content": content_rows}}
        logger.info("feishu_post_blocks_payload", chat_id=chat_id, payload=payload)
        body_builder = (
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("post")
            .content(json.dumps(payload, ensure_ascii=False))
        )
        self._set_thread_id(body_builder, root_id)
        req = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(body_builder.build())
            .build()
        )
        try:
            resp = self._client.im.v1.message.create(req)
            data = getattr(resp, "data", None)
            message_id = getattr(data, "message_id", None)
            logger.info("feishu_post_sent", chat_id=chat_id, message_id=message_id)
            return message_id
        except Exception as exc:
            logger.warning("feishu_post_send_failed", chat_id=chat_id, error=str(exc))
            return None

    async def _send_text_notice(self, chat_id: str, title: str, lines: list[str], root_id: str = "") -> Optional[str]:
        if not self._client:
            return None
        text = "\n".join([title] + lines)
        logger.info("feishu_text_notice_payload", chat_id=chat_id, text=text)
        content = json.dumps({"text": text}, ensure_ascii=False)
        body_builder = (
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("text")
            .content(content)
        )
        self._set_thread_id(body_builder, root_id)
        req = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(body_builder.build())
            .build()
        )
        try:
            resp = self._client.im.v1.message.create(req)
            data = getattr(resp, "data", None)
            message_id = getattr(data, "message_id", None)
            logger.info("feishu_text_sent", chat_id=chat_id, message_id=message_id)
            return message_id
        except Exception as exc:
            logger.warning("feishu_text_send_failed", chat_id=chat_id, error=str(exc))
            return None

    def _extract_announcement_block_ids(self, content: str) -> list[str]:
        try:
            data = json.loads(content) if content else {}
        except json.JSONDecodeError:
            return []
        blocks = data.get("blocks") if isinstance(data, dict) else None
        if not isinstance(blocks, list):
            return []
        block_ids: list[str] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_id = block.get("block_id") or block.get("blockId")
            if isinstance(block_id, str):
                block_ids.append(block_id)
        return block_ids

    def _build_announcement_payload(self, lines: list[str]) -> str:
        blocks = []
        for line in lines:
            blocks.append(
                {
                    "type": "paragraph",
                    "paragraph": {
                        "elements": [{"type": "textRun", "textRun": {"text": line, "style": {}}}],
                        "style": {},
                    },
                }
            )
        payload = {"blocks": blocks}
        return json.dumps(payload, ensure_ascii=False)

    async def _update_chat_announcement(self, chat_id: str, lines: list[str]) -> None:
        if not self._client or not chat_id:
            return
        try:
            get_req = GetChatAnnouncementRequest.builder().chat_id(chat_id).build()
            option = None
            token_type = "tenant"
            get_resp = self._client.im.v1.chat_announcement.get(get_req, option)
            revision = "0"
            content = ""
            if getattr(get_resp, "success", lambda: False)():
                data = getattr(get_resp, "data", None)
                if data:
                    revision = getattr(data, "revision", None) or revision
                    content = getattr(data, "content", "") or ""
            block_ids = self._extract_announcement_block_ids(content)
            requests: list[str] = []
            if block_ids:
                requests.append(
                    json.dumps(
                        {
                            "deleteBlocksRequest": {"blockIds": block_ids},
                            "requestType": "DeleteBlocksRequestType",
                        },
                        ensure_ascii=False,
                    )
                )
            requests.append(
                json.dumps(
                    {
                        "insertBlocksRequest": {
                            "location": {"endOfZone": True, "index": 0, "zoneId": "0"},
                            "payload": self._build_announcement_payload(lines),
                        },
                        "requestType": "InsertBlocksRequestType",
                    },
                    ensure_ascii=False,
                )
            )
            patch_req = (
                PatchChatAnnouncementRequest.builder()
                .chat_id(chat_id)
                .request_body(
                    PatchChatAnnouncementRequestBody.builder()
                    .revision(str(revision))
                    .requests(requests)
                    .build()
                )
                .build()
            )
            patch_resp = self._client.im.v1.chat_announcement.patch(patch_req, option)
            if getattr(patch_resp, "success", lambda: False)():
                logger.info(
                    "feishu_announcement_updated",
                    chat_id=chat_id,
                    revision=revision,
                    token_type=token_type,
                )
            else:
                logger.warning(
                    "feishu_announcement_update_failed",
                    chat_id=chat_id,
                    token_type=token_type,
                    code=getattr(patch_resp, "code", None),
                    msg=getattr(patch_resp, "msg", None),
                )
        except Exception as exc:
            logger.warning("feishu_announcement_update_failed", chat_id=chat_id, error=str(exc))

    async def _pin_message(self, message_id: Optional[str], chat_id: Optional[str] = None) -> None:
        if not self._client or not message_id:
            return
        try:
            body = CreatePinRequestBody.builder().message_id(message_id).build()
            req = CreatePinRequest.builder().request_body(body).build()
            pin_resp = self._client.im.v1.pin.create(req)
            pin_success = getattr(pin_resp, "success", lambda: False)()
            pin_code = getattr(pin_resp, "code", None)
            if callable(getattr(pin_resp, "get_code", None)):
                pin_code = pin_resp.get_code()
            pin_msg = getattr(pin_resp, "msg", None)
            if callable(getattr(pin_resp, "get_msg", None)):
                pin_msg = pin_resp.get_msg()
            if pin_success:
                logger.info("feishu_pin_set", message_id=message_id, code=pin_code, msg=pin_msg)
            else:
                logger.warning("feishu_pin_failed", message_id=message_id, code=pin_code, msg=pin_msg)
        except Exception as exc:
            logger.warning("feishu_pin_failed", error=str(exc))
            try:
                body = CreatePinRequestBody.builder().message_id(message_id).build()
                req = CreatePinRequest.builder().request_body(body).build()
                pin_resp = self._client.im.v1.pin.create(req)
                pin_success = getattr(pin_resp, "success", lambda: False)()
                pin_code = getattr(pin_resp, "code", None)
                if callable(getattr(pin_resp, "get_code", None)):
                    pin_code = pin_resp.get_code()
                pin_msg = getattr(pin_resp, "msg", None)
                if callable(getattr(pin_resp, "get_msg", None)):
                    pin_msg = pin_resp.get_msg()
                if pin_success:
                    logger.info("feishu_pin_set", message_id=message_id, code=pin_code, msg=pin_msg)
                else:
                    logger.warning("feishu_pin_failed", message_id=message_id, code=pin_code, msg=pin_msg)
            except Exception as pin_exc:
                logger.warning("feishu_pin_failed", error=str(pin_exc))

    @staticmethod
    def _chunk_text(text: str, size: int) -> list[str]:
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start:start + size])
            start += size
        return chunks

    @staticmethod
    def _set_thread_id(builder: Any, root_id: str) -> None:
        if not root_id:
            return
        if hasattr(builder, "root_id"):
            builder.root_id(root_id)
        elif hasattr(builder, "parent_id"):
            builder.parent_id(root_id)


feishu_bot = FeishuBot()
