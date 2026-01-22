"""
会话扫描器

扫描 Codex 和 Gemini 的会话文件
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger()


class CodexSessionScanner:
    """
    Codex 会话扫描器

    从 ~/.codex/sessions/ 目录扫描会话文件
    """

    def __init__(self, codex_dir: Optional[Path] = None):
        """
        初始化扫描器

        Args:
            codex_dir: Codex 配置目录，默认为 ~/.codex
        """
        if codex_dir is None:
            codex_dir = Path.home() / ".codex"
        self._codex_dir = codex_dir
        self._sessions_dir = codex_dir / "sessions"

    def list_sessions(self) -> List[Dict]:
        """
        列出所有 Codex 会话

        Returns:
            会话列表，每个会话包含：
            - id: 会话 ID
            - projectPath: 项目路径
            - created_at: 创建时间
            - first_message: 第一条用户消息
            - model: 使用的模型
            - engine: "codex"
        """
        logger.info("codex_sessions_scan_start", sessions_dir=str(self._sessions_dir))

        if not self._sessions_dir.exists():
            logger.warning("codex_sessions_dir_missing", path=str(self._sessions_dir))
            return []

        sessions = []

        try:
            # 递归扫描所有 .jsonl 文件
            for session_file in self._sessions_dir.rglob("*.jsonl"):
                try:
                    session_id = session_file.stem

                    # 获取文件创建时间
                    stat = session_file.stat()
                    created_at = int(stat.st_ctime)

                    # 提取项目路径和第一条消息
                    project_path, first_message, model = self._extract_session_info(session_file)

                    if not project_path:
                        logger.debug("codex_session_no_project_path", session_id=session_id)
                        continue

                    sessions.append({
                        "id": session_id,
                        "projectPath": project_path,
                        "created_at": created_at,
                        "first_message": first_message,
                        "model": model,
                        "engine": "codex",
                    })

                except OSError as exc:
                    logger.debug("codex_session_read_failed",
                               file=str(session_file), error=str(exc))
                    continue

        except OSError as exc:
            logger.error("codex_sessions_scan_failed", error=str(exc))
            return []

        # 按创建时间降序排序
        sessions.sort(key=lambda s: s["created_at"], reverse=True)

        logger.info("codex_sessions_scan_complete", count=len(sessions))
        return sessions

    def _extract_session_info(self, session_file: Path) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        从会话文件中提取项目路径、第一条消息和模型

        Args:
            session_file: 会话文件路径

        Returns:
            (project_path, first_message, model) 元组
        """
        project_path = None
        first_message = None
        model = None

        try:
            with session_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        # 🔥 Codex 格式：cwd 在 payload 内
                        # {"type":"session_meta","payload":{"cwd":"/path/to/project"}}
                        payload = data.get("payload", {})

                        # 提取项目路径
                        if not project_path:
                            project_path = (
                                payload.get("cwd") or
                                payload.get("projectPath") or
                                data.get("cwd") or
                                data.get("projectPath")
                            )

                        # 提取模型
                        if not model:
                            model = payload.get("model") or data.get("model")

                        # 🔥 Codex 格式：用户消息在 response_item 类型中
                        # {"type":"response_item","payload":{"role":"user","content":[{"type":"input_text","text":"..."}]}}
                        if not first_message and data.get("type") == "response_item":
                            if payload.get("role") == "user":
                                content = payload.get("content", [])
                                if isinstance(content, list):
                                    for item in content:
                                        if isinstance(item, dict) and item.get("type") == "input_text":
                                            text = item.get("text", "")
                                            # 跳过系统消息
                                            if text and not text.startswith("<environment_context>"):
                                                first_message = text[:200] if len(text) > 200 else text
                                                break

                        # 如果都找到了，可以提前退出
                        if project_path and first_message and model:
                            break

                    except json.JSONDecodeError:
                        continue

        except OSError:
            pass

        return project_path, first_message, model


class GeminiSessionScanner:
    """
    Gemini 会话扫描器

    从 ~/.gemini/tmp/{project_hash}/chats/*.json 目录扫描会话文件

    🔥 重要：Gemini 会话文件中没有 projectPath 字段，需要通过 project_path 计算 hash 来定位
    """

    def __init__(self, gemini_dir: Optional[Path] = None):
        """
        初始化扫描器

        Args:
            gemini_dir: Gemini 配置目录，默认为 ~/.gemini
        """
        if gemini_dir is None:
            gemini_dir = Path.home() / ".gemini"
        self._gemini_dir = gemini_dir
        self._tmp_dir = gemini_dir / "tmp"

    def list_sessions(self, project_path: Optional[str] = None) -> List[Dict]:
        """
        列出 Gemini 会话

        Args:
            project_path: 项目路径。如果提供，只返回该项目的会话；否则扫描所有项目

        Returns:
            会话列表，每个会话包含：
            - id: 会话 ID
            - projectPath: 项目路径
            - created_at: 创建时间
            - first_message: 第一条用户消息
            - model: 使用的模型
            - engine: "gemini"
        """
        logger.info("gemini_sessions_scan_start", tmp_dir=str(self._tmp_dir), project_path=project_path)

        if not self._tmp_dir.exists():
            logger.warning("gemini_tmp_dir_missing", path=str(self._tmp_dir))
            return []

        sessions = []

        try:
            if project_path:
                # 🔥 如果指定了项目路径，计算 hash 并只扫描该目录
                project_hash = self._hash_project_path(project_path)
                project_dir = self._tmp_dir / project_hash
                if project_dir.exists():
                    sessions.extend(self._scan_project_dir(project_dir, project_path))
            else:
                # 扫描所有项目目录
                for project_dir in self._tmp_dir.iterdir():
                    if not project_dir.is_dir():
                        continue
                    # 尝试从 logs.json 获取项目路径
                    detected_path = self._detect_project_path(project_dir)
                    sessions.extend(self._scan_project_dir(project_dir, detected_path))

        except OSError as exc:
            logger.error("gemini_sessions_scan_failed", error=str(exc))
            return []

        # 按创建时间降序排序
        sessions.sort(key=lambda s: s["created_at"], reverse=True)

        logger.info("gemini_sessions_scan_complete", count=len(sessions))
        return sessions

    def _hash_project_path(self, project_path: str) -> str:
        """计算项目路径的 SHA256 hash（与 Gemini CLI 行为一致）"""
        import hashlib
        return hashlib.sha256(project_path.encode()).hexdigest()

    def _detect_project_path(self, project_dir: Path) -> Optional[str]:
        """
        尝试从 logs.json 或其他文件检测项目路径

        Gemini CLI 在 logs.json 中记录了项目信息
        """
        logs_file = project_dir / "logs.json"
        if logs_file.exists():
            try:
                logs = json.loads(logs_file.read_text(encoding="utf-8"))
                if isinstance(logs, list) and logs:
                    # logs.json 是一个数组，每项包含 cwd
                    return logs[0].get("cwd")
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def _scan_project_dir(self, project_dir: Path, project_path: Optional[str]) -> List[Dict]:
        """扫描单个项目目录的所有会话"""
        sessions = []
        chats_dir = project_dir / "chats"

        if not chats_dir.exists():
            return sessions

        for session_file in chats_dir.glob("*.json"):
            try:
                session_info = self._parse_session_file(session_file, project_path)
                if session_info:
                    sessions.append(session_info)
            except Exception as exc:
                logger.debug(
                    "gemini_session_parse_failed",
                    file=str(session_file),
                    error=str(exc)
                )
                continue

        return sessions

    def _parse_session_file(self, session_file: Path, project_path_from_hash: Optional[str] = None) -> Optional[Dict]:
        """
        解析 Gemini 会话文件

        Args:
            session_file: 会话文件路径
            project_path_from_hash: 从 hash 映射获取的项目路径

        Returns:
            会话信息字典，如果解析失败返回 None
        """
        try:
            content = json.loads(session_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        session_id = content.get("sessionId") or session_file.stem
        # 🔥 Gemini 会话文件中可能没有 projectPath，使用传入的映射值
        project_path = content.get("projectPath") or content.get("cwd") or project_path_from_hash

        # 解析 startTime（可能是 ISO 字符串或时间戳）
        start_time_raw = content.get("startTime", 0)
        if isinstance(start_time_raw, str):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(start_time_raw.replace("Z", "+00:00"))
                start_time = int(dt.timestamp())
            except (ValueError, TypeError):
                start_time = 0
        else:
            start_time = start_time_raw

        # 从消息中提取模型
        model = content.get("model") or self._extract_model_from_messages(content)

        # 提取第一条用户消息
        first_message = self._extract_first_message(content)

        # 跳过子代理会话（以 "Your task is to" 开头）
        if first_message and first_message.strip().startswith("Your task is to"):
            return None

        # 🔥 如果无法获取项目路径，使用 projectHash 作为标识
        # 这样至少能在会话列表中显示，用户可以点击查看历史
        if not project_path:
            project_hash = content.get("projectHash")
            if project_hash:
                project_path = f"[hash:{project_hash[:8]}]"
            else:
                return None

        return {
            "id": session_id,
            "projectPath": project_path,
            "project_path": project_path,  # 兼容两种格式
            "created_at": start_time,
            "first_message": first_message,
            "model": model,
            "engine": "gemini",
        }

    def _extract_model_from_messages(self, content: Dict) -> Optional[str]:
        """从消息中提取使用的模型"""
        messages = content.get("messages", [])
        for msg in messages:
            if msg.get("type") == "gemini":
                model = msg.get("model")
                if model:
                    return model
        return None

    def _extract_first_message(self, content: Dict) -> Optional[str]:
        """
        从会话内容中提取第一条用户消息

        Args:
            content: 会话 JSON 内容

        Returns:
            第一条用户消息，如果不存在返回 None
        """
        messages = content.get("messages", [])
        if not messages:
            return None

        for msg in messages:
            # 检查消息类型
            msg_type = msg.get("type")
            if msg_type == "user" or msg_type == "human":
                # 提取内容
                msg_content = msg.get("content")
                if isinstance(msg_content, str):
                    return msg_content[:200] if len(msg_content) > 200 else msg_content
                elif isinstance(msg_content, list):
                    # 内容可能是数组格式
                    for item in msg_content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text = item.get("text", "")
                            return text[:200] if len(text) > 200 else text

        return None
