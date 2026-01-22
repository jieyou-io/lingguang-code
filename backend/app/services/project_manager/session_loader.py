"""
会话历史加载器

从 JSONL 文件加载会话消息历史
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class ClaudeSessionLoader:
    """
    Claude 会话历史加载器

    从 ~/.claude/projects/{project_id}/{session_id}.jsonl 加载会话消息
    """

    def __init__(self, claude_dir: Optional[Path] = None):
        """
        初始化加载器

        Args:
            claude_dir: Claude 配置目录，默认为 ~/.claude
        """
        if claude_dir is None:
            claude_dir = Path.home() / ".claude"
        self._claude_dir = claude_dir
        self._projects_dir = claude_dir / "projects"

    def load_session_history(self, session_id: str, project_id: str) -> List[Dict[str, Any]]:
        """
        加载会话历史消息

        Args:
            session_id: 会话 ID
            project_id: 项目 ID（目录名，可能是新格式或旧格式）

        Returns:
            消息列表，按时间戳排序

        Raises:
            FileNotFoundError: 会话文件不存在
        """
        logger.info("load_session_history", session_id=session_id, project_id=project_id)

        # 🔥 尝试直接匹配（新格式或旧格式）
        project_dir = self._projects_dir / project_id
        session_path = project_dir / f"{session_id}.jsonl"

        if not session_path.exists():
            # 🔥 如果新格式不存在，尝试转换为旧格式
            # 新格式: -Users-king-Documents-ai--code -> 旧格式: -Users-king-Documents-ai-code
            old_format_id = project_id.replace("--", "-")
            project_dir = self._projects_dir / old_format_id
            session_path = project_dir / f"{session_id}.jsonl"

            if not session_path.exists():
                raise FileNotFoundError(f"Session file not found: {session_id}")

        # 获取文件修改时间作为基准时间
        stat = session_path.stat()
        base_time = datetime.fromtimestamp(stat.st_mtime)

        messages = []
        agent_to_tool_use_id = {}

        # Step 1: 加载主会话消息并构建 agentId -> tool_use_id 映射
        try:
            with session_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        json_obj = json.loads(line)

                        # 检查是否有 tool_result 包含 agentId
                        message = json_obj.get("message", {})
                        content = message.get("content")

                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "tool_result":
                                    tool_use_id = item.get("tool_use_id")
                                    tool_use_result = json_obj.get("toolUseResult", {})

                                    # 确保 tool_use_result 是字典
                                    if isinstance(tool_use_result, dict):
                                        agent_id = tool_use_result.get("agentId")

                                        if tool_use_id and agent_id:
                                            logger.debug("found_agent_mapping",
                                                       agent_id=agent_id,
                                                       tool_use_id=tool_use_id)
                                            agent_to_tool_use_id[agent_id] = tool_use_id

                        messages.append(json_obj)

                    except json.JSONDecodeError as exc:
                        logger.debug("json_decode_error", line=line[:100], error=str(exc))
                        continue

        except OSError as exc:
            logger.error("session_file_read_failed", path=str(session_path), error=str(exc))
            raise

        logger.info("agent_mappings_found", count=len(agent_to_tool_use_id))

        # Step 2: 加载子代理消息（agent-*.jsonl 文件）
        if agent_to_tool_use_id:
            self._load_subagent_messages(
                project_dir,
                session_id,
                agent_to_tool_use_id,
                messages
            )

        # Step 3: 按时间戳排序
        messages.sort(key=lambda m: m.get("timestamp", ""))

        # Step 4: 为没有时间戳的历史消息添加时间戳
        self._add_missing_timestamps(messages, base_time)

        logger.info("session_history_loaded",
                   session_id=session_id,
                   message_count=len(messages))

        return messages

    def _load_subagent_messages(
        self,
        project_dir: Path,
        session_id: str,
        agent_to_tool_use_id: Dict[str, str],
        messages: List[Dict[str, Any]]
    ) -> None:
        """
        加载子代理消息

        Args:
            project_dir: 项目目录
            session_id: 会话 ID
            agent_to_tool_use_id: agentId -> tool_use_id 映射
            messages: 消息列表（会被修改）
        """
        try:
            for entry in project_dir.iterdir():
                if not entry.is_file():
                    continue

                file_name = entry.name
                # 匹配 agent-*.jsonl 文件
                if file_name.startswith("agent-") and file_name.endswith(".jsonl"):
                    # 提取 agentId (例如: "agent-aa740fde.jsonl" -> "aa740fde")
                    agent_id = file_name.removeprefix("agent-").removesuffix(".jsonl")

                    # 检查这个 agent 是否属于当前会话
                    tool_use_id = agent_to_tool_use_id.get(agent_id)
                    if not tool_use_id:
                        continue

                    logger.info("loading_subagent_file",
                              file_name=file_name,
                              tool_use_id=tool_use_id)

                    # 加载子代理消息
                    self._load_subagent_file(entry, session_id, tool_use_id, messages)

        except OSError as exc:
            logger.warning("subagent_scan_failed", error=str(exc))

    def _load_subagent_file(
        self,
        file_path: Path,
        session_id: str,
        tool_use_id: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """
        加载单个子代理文件

        Args:
            file_path: 子代理文件路径
            session_id: 会话 ID
            tool_use_id: 父工具调用 ID
            messages: 消息列表（会被修改）
        """
        try:
            with file_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        json_obj = json.loads(line)

                        # 验证这个子代理属于当前会话
                        subagent_session_id = json_obj.get("sessionId")
                        if subagent_session_id == session_id:
                            # 添加 parent_tool_use_id 链接到 Task 工具
                            json_obj["parent_tool_use_id"] = tool_use_id
                            messages.append(json_obj)

                    except json.JSONDecodeError:
                        continue

        except OSError as exc:
            logger.warning("subagent_file_read_failed",
                         path=str(file_path), error=str(exc))

    def _add_missing_timestamps(
        self,
        messages: List[Dict[str, Any]],
        base_time: datetime
    ) -> None:
        """
        为没有时间戳的历史消息添加时间戳

        Args:
            messages: 消息列表（会被修改）
            base_time: 基准时间
        """
        messages_count = len(messages)

        for i, message in enumerate(messages):
            message_type = message.get("type", "")

            # 计算消息时间戳（每条消息间隔 5 秒，越早的消息时间越早）
            time_offset = (messages_count - i - 1) * 5  # 5 秒间隔
            message_time = base_time - timedelta(seconds=time_offset)
            timestamp_iso = message_time.isoformat() + "Z"

            # 根据消息类型设置时间戳字段
            if message_type == "user":
                if "sentAt" not in message:
                    message["sentAt"] = timestamp_iso
            elif message_type in ("assistant", "system", "result"):
                if "receivedAt" not in message:
                    message["receivedAt"] = timestamp_iso
            else:
                # 未知类型，添加 receivedAt
                if "receivedAt" not in message:
                    message["receivedAt"] = timestamp_iso


class CodexSessionLoader:
    """
    Codex 会话历史加载器

    从 ~/.codex/sessions/{year}/{month}/{day}/{session_id}.jsonl 加载会话消息
    """

    def __init__(self, codex_dir: Optional[Path] = None):
        """
        初始化加载器

        Args:
            codex_dir: Codex 配置目录，默认为 ~/.codex
        """
        if codex_dir is None:
            codex_dir = Path.home() / ".codex"
        self._codex_dir = codex_dir
        self._sessions_dir = codex_dir / "sessions"

    def load_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        加载 Codex 会话历史消息

        Args:
            session_id: 会话 ID

        Returns:
            消息列表

        Raises:
            FileNotFoundError: 会话文件不存在
        """
        logger.info("load_codex_session_history", session_id=session_id)

        # 在 sessions 目录下递归查找会话文件
        session_file = None
        for file_path in self._sessions_dir.rglob(f"{session_id}.jsonl"):
            session_file = file_path
            break

        if not session_file or not session_file.exists():
            raise FileNotFoundError(f"Codex session file not found: {session_id}")

        messages = []

        try:
            with session_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        json_obj = json.loads(line)
                        messages.append(json_obj)
                    except json.JSONDecodeError as exc:
                        logger.debug("json_decode_error", line=line[:100], error=str(exc))
                        continue

        except OSError as exc:
            logger.error("codex_session_file_read_failed",
                       path=str(session_file), error=str(exc))
            raise

        logger.info("codex_session_history_loaded",
                   session_id=session_id,
                   message_count=len(messages))

        return messages


class GeminiSessionLoader:
    """
    Gemini 会话历史加载器

    从 ~/.gemini/tmp/{project_hash}/chats/*.json 目录加载会话消息
    """

    def __init__(self, gemini_dir: Optional[Path] = None):
        """
        初始化加载器

        Args:
            gemini_dir: Gemini 配置目录，默认为 ~/.gemini
        """
        if gemini_dir is None:
            gemini_dir = Path.home() / ".gemini"
        self._gemini_dir = gemini_dir
        self._tmp_dir = gemini_dir / "tmp"

    def load_session_history(self, session_id: str) -> Dict[str, Any]:
        """
        加载 Gemini 会话历史消息

        Args:
            session_id: 会话 ID

        Returns:
            包含 messages 和 project_path 的字典

        Raises:
            FileNotFoundError: 会话文件不存在
        """
        logger.info("load_gemini_session_history", session_id=session_id)

        # 在所有项目目录的 chats 文件夹中查找会话文件
        session_file = None
        project_path = None
        for project_dir in self._tmp_dir.iterdir():
            if not project_dir.is_dir():
                continue
            chats_dir = project_dir / "chats"
            if not chats_dir.exists():
                continue

            # 查找匹配 sessionId 的文件
            for json_file in chats_dir.glob("*.json"):
                try:
                    content = json.loads(json_file.read_text(encoding="utf-8"))
                    if content.get("sessionId") == session_id:
                        session_file = json_file
                        # 🔥 从会话文件中提取项目路径
                        project_path = content.get("projectPath")
                        break
                except (json.JSONDecodeError, OSError):
                    continue

            if session_file:
                break

        if not session_file:
            raise FileNotFoundError(f"Gemini session file not found: {session_id}")

        # 读取会话文件
        try:
            content = json.loads(session_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("gemini_session_file_read_failed", error=str(exc))
            raise FileNotFoundError(f"Failed to read Gemini session: {session_id}")

        # 转换消息格式为前端期望的格式
        raw_messages = content.get("messages", [])
        messages = []

        for msg in raw_messages:
            msg_type = msg.get("type", "")
            msg_content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            # 转换为前端期望的格式
            if msg_type == "user" or msg_type == "human":
                messages.append({
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": msg_content,
                    },
                    "sentAt": timestamp,
                    "messageId": msg.get("id", ""),
                })
            elif msg_type == "gemini" or msg_type == "assistant":
                messages.append({
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": msg_content,
                    },
                    "receivedAt": timestamp,
                    "messageId": msg.get("id", ""),
                })

        logger.info("gemini_session_history_loaded",
                   session_id=session_id,
                   message_count=len(messages))

        # 🔥 返回包含消息和项目路径的字典
        return {
            "messages": messages,
            "project_path": project_path,
        }
