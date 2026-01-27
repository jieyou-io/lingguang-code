"""
Claude 项目扫描器

"""
import json
from pathlib import Path
from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger()


class ClaudeProjectScanner:
    """
    Claude 项目扫描器

    从 ~/.claude/projects/ 目录扫描项目，读取会话文件提取项目信息。
    """

    def __init__(self, claude_dir: Optional[Path] = None):
        """
        初始化扫描器

        Args:
            claude_dir: Claude 配置目录，默认为 ~/.claude
        """
        if claude_dir is None:
            claude_dir = Path.home() / ".claude"
        self._claude_dir = claude_dir
        self._projects_dir = claude_dir / "projects"
        self._todos_dir = claude_dir / "todos"

    def list_projects(self) -> List[Dict]:
        """
        列出所有项目

        Returns:
            项目列表，每个项目包含：
            - id: 项目目录名
            - path: 实际项目路径（从会话文件中提取）
            - sessions: 会话 ID 列表
            - created_at: 最后活跃时间（Unix 时间戳）
        """
        logger.info("claude_project_scan_start", projects_dir=str(self._projects_dir))

        if not self._projects_dir.exists():
            logger.warning("claude_projects_dir_missing", path=str(self._projects_dir))
            return []

        projects = []

        try:
            for project_dir in self._projects_dir.iterdir():
                if not project_dir.is_dir():
                    continue

                project_id = project_dir.name

                # 从会话文件中提取项目路径（如果失败则使用目录名解码）
                project_path = self._get_project_path_from_sessions(project_dir)

                # 扫描会话文件
                sessions = []
                latest_activity = 0

                try:
                    for session_file in project_dir.glob("*.jsonl"):
                        # 跳过 agent-*.jsonl 文件（子代理会话）
                        if session_file.stem.startswith("agent-"):
                            continue

                        session_id = session_file.stem
                        sessions.append(session_id)

                        # 获取文件修改时间作为最后活跃时间
                        try:
                            mtime = session_file.stat().st_mtime
                            if mtime > latest_activity:
                                latest_activity = mtime
                        except OSError:
                            pass

                except OSError as exc:
                    logger.warning("claude_project_sessions_scan_failed",
                                 project_id=project_id, error=str(exc))
                    continue

                # 如果没有会话，跳过
                if not sessions:
                    logger.debug("claude_project_no_sessions", project_id=project_id)
                    continue

                # 如果没有活跃时间，使用目录创建时间
                if latest_activity == 0:
                    try:
                        latest_activity = project_dir.stat().st_mtime
                    except OSError:
                        latest_activity = 0

                projects.append({
                    "id": project_id,
                    "path": project_path,
                    "sessions": sessions,
                    "created_at": int(latest_activity),
                })

        except OSError as exc:
            logger.error("claude_projects_scan_failed", error=str(exc))
            return []

        # 按最后活跃时间降序排序
        projects.sort(key=lambda p: p["created_at"], reverse=True)

        logger.info("claude_project_scan_complete", count=len(projects))
        return projects

    def _get_project_path_from_sessions(self, project_dir: Path) -> Optional[str]:
        """
        从会话文件中提取项目路径

        读取 .jsonl 文件，查找包含 cwd 字段的行。

        Args:
            project_dir: 项目目录路径

        Returns:
            项目路径，如果无法提取则使用目录名解码
        """
        try:
            for session_file in project_dir.glob("*.jsonl"):
                # 跳过 agent-*.jsonl 文件
                if session_file.stem.startswith("agent-"):
                    continue

                try:
                    with session_file.open("r", encoding="utf-8", errors="ignore") as f:
                        # 读取前几行，查找 cwd 字段
                        for _ in range(10):  # 最多读取前10行
                            line = f.readline().strip()
                            if not line:
                                break

                            try:
                                data = json.loads(line)
                                cwd = data.get("cwd")
                                if cwd:
                                    # 清理路径（移除双反斜杠）
                                    cleaned_cwd = cwd.replace("\\\\", "\\")
                                    return cleaned_cwd
                            except json.JSONDecodeError:
                                continue

                except (OSError, json.JSONDecodeError) as exc:
                    logger.debug("claude_session_read_failed",
                               file=str(session_file), error=str(exc))
                    continue

        except OSError:
            pass

        # 如果无法从会话文件中提取，尝试从目录名解码
        return self._decode_project_path(project_dir.name)

    def _decode_project_path(self, encoded_name: str) -> str:
        """
        从编码的目录名解码项目路径

        🔥 支持两种编码格式：
        1. 新格式：-- 表示原有的 -，- 表示 /
           例如: -Users-king-Documents-ai--code -> /Users/king/Documents/ai-code
        2. 旧格式：Claude CLI 原生格式，- 表示 /
           例如: -Users-king-Documents-project -> /Users/king/Documents/project

        Args:
            encoded_name: 编码的目录名

        Returns:
            解码后的项目路径
        """
        if not encoded_name:
            return encoded_name

        # 🔥 检测是否包含 --（新格式）
        if "--" in encoded_name:
            # 新格式：使用占位符来正确处理 -- -> -
            placeholder = "\x00"
            decoded = encoded_name.replace("--", placeholder).replace("-", "/").replace(placeholder, "-")
        else:
            # 旧格式：直接替换 - 为 /
            decoded = encoded_name.replace("-", "/")

        return decoded

    def get_project_sessions(self, project_id: str) -> List[Dict]:
        """
        获取指定项目的所有会话详情

        Args:
            project_id: 项目 ID（目录名，可能是新格式或旧格式）

        Returns:
            会话列表，每个会话包含：
            - id: 会话 ID
            - project_id: 项目 ID
            - project_path: 项目路径
            - todo_data: Todo 数据
            - created_at: 创建时间
            - first_message: 第一条用户消息
            - message_timestamp: 消息时间戳
            - last_message_timestamp: 最后消息时间戳
            - model: 使用的模型
            - engine: 执行引擎
        """
        logger.info("claude_get_project_sessions", project_id=project_id)

        # 🔥 尝试直接匹配（新格式或旧格式）
        project_dir = self._projects_dir / project_id
        if not project_dir.exists():
            # 🔥 如果新格式不存在，尝试转换为旧格式
            # 新格式: -Users-king-Documents-ai--code -> 旧格式: -Users-king-Documents-ai-code
            old_format_id = project_id.replace("--", "-")
            project_dir = self._projects_dir / old_format_id
            if not project_dir.exists():
                logger.warning("claude_project_not_found", project_id=project_id, old_format_id=old_format_id)
                return []
            logger.info("claude_project_found_with_old_format", project_id=project_id, old_format_id=old_format_id)

        # 获取项目路径
        project_path = self._get_project_path_from_sessions(project_dir)

        sessions = []

        try:
            for session_file in project_dir.glob("*.jsonl"):
                # 跳过 agent-*.jsonl 文件（子代理会话）
                if session_file.stem.startswith("agent-"):
                    continue

                session_id = session_file.stem

                # 获取文件创建时间
                try:
                    stat = session_file.stat()
                    created_at = int(stat.st_ctime)
                except OSError:
                    created_at = 0

                # 提取第一条用户消息和时间戳
                first_message, message_timestamp = self._extract_first_user_message(session_file)

                # 提取最后消息时间戳
                last_message_timestamp = self._extract_last_message_timestamp(session_file)

                # Claude 会话均来自 ~/.claude/projects，固定标记为 claude
                engine = "claude"

                # 提取使用的模型（传入引擎参数以获取正确的默认模型）
                model = self._extract_session_model(session_file, engine)

                # Fallback: 如果 first_message 为空，使用默认文本
                if not first_message:
                    # 检查会话是否真的有内容
                    has_content = last_message_timestamp is not None and stat.st_size > 100
                    if has_content:
                        # 只显示 session_id 的前8位
                        short_id = session_id[:8] if len(session_id) >= 8 else session_id
                        first_message = f"Resumed Session ({short_id}...)"

                # 读取 Todo 数据
                todo_path = self._todos_dir / f"{session_id}.json"
                todo_data = None
                if todo_path.exists():
                    try:
                        with todo_path.open("r", encoding="utf-8", errors="ignore") as f:
                            todo_data = json.load(f)
                    except (OSError, json.JSONDecodeError) as exc:
                        logger.debug("claude_todo_read_failed",
                                   session_id=session_id, error=str(exc))

                sessions.append({
                    "id": session_id,
                    "project_id": project_id,
                    "project_path": project_path,
                    "todo_data": todo_data,
                    "created_at": created_at,
                    "first_message": first_message,
                    "message_timestamp": message_timestamp,
                    "last_message_timestamp": last_message_timestamp,
                    "model": model,
                    "engine": engine,
                })

        except OSError as exc:
            logger.error("claude_sessions_scan_failed",
                       project_id=project_id, error=str(exc))
            return []

        # 按创建时间降序排序
        sessions.sort(key=lambda s: s["created_at"], reverse=True)

        logger.info("claude_get_project_sessions_complete",
                   project_id=project_id, count=len(sessions))
        return sessions

    def _extract_first_user_message(self, session_file: Path) -> tuple[Optional[str], Optional[str]]:
        """
        提取第一条用户消息和时间戳

        Args:
            session_file: 会话文件路径

        Returns:
            (first_message, message_timestamp) 元组
        """
        try:
            with session_file.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        message = data.get("message", {})
                        if message.get("role") == "user":
                            content = message.get("content")
                            timestamp = data.get("timestamp")

                            # 提取文本内容
                            if isinstance(content, str):
                                return content, timestamp
                            elif isinstance(content, list):
                                # 从数组中提取文本
                                for item in content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        return item.get("text"), timestamp
                    except json.JSONDecodeError:
                        continue

        except OSError:
            pass

        return None, None

    def _extract_last_message_timestamp(self, session_file: Path) -> Optional[str]:
        """
        提取最后一条消息的时间戳

        Args:
            session_file: 会话文件路径

        Returns:
            最后消息时间戳（ISO 字符串）
        """
        last_timestamp = None

        try:
            with session_file.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        timestamp = data.get("timestamp")
                        if timestamp:
                            last_timestamp = timestamp
                    except json.JSONDecodeError:
                        continue

        except OSError:
            pass

        return last_timestamp

    def _extract_session_model(self, session_file: Path, engine: Optional[str] = None) -> Optional[str]:
        """
        提取会话使用的模型

        Args:
            session_file: 会话文件路径
            engine: 引擎类型（用于返回默认模型）

        Returns:
            模型名称
        """
        default_model = self._get_default_model()
        try:
            with session_file.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        # 先检查顶层 model 字段
                        model = data.get("model")
                        if model and model != "<synthetic>":
                            return model

                        # 再检查 message.model 字段（Claude 会话通常在这里）
                        message = data.get("message", {})
                        if isinstance(message, dict):
                            model = message.get("model")
                            if model and model != "<synthetic>":
                                return model
                    except json.JSONDecodeError:
                        continue

        except OSError:
            pass

        return default_model

    def _get_default_model(self) -> Optional[str]:
        """从 ~/.claude/config.json 读取默认模型（优先 Sonnet）"""
        try:
            config_path = self._claude_dir / "config.json"
            if config_path.exists():
                with config_path.open("r", encoding="utf-8") as f:
                    config = json.load(f)
                env = config.get("env", {})
                sonnet = env.get("ANTHROPIC_DEFAULT_SONNET_MODEL") or env.get("ANTHROPIC_MODEL")
                if sonnet:
                    return sonnet
                opus = env.get("ANTHROPIC_DEFAULT_OPUS_MODEL")
                if opus:
                    return opus
                haiku = env.get("ANTHROPIC_DEFAULT_HAIKU_MODEL")
                if haiku:
                    return haiku
                reasoning = env.get("ANTHROPIC_REASONING_MODEL")
                if reasoning:
                    return reasoning
        except Exception:
            return None
        return None

        # 如果没有找到模型，根据引擎返回默认模型
        if engine == "codex":
            return "gpt-5"
        elif engine == "gemini":
            return "gemini-2.5-pro"
        elif engine == "claude":
            return "claude-sonnet-4-5"

        return None

    def _detect_session_engine(self, session_file: Path) -> Optional[str]:
        """
        检测会话使用的执行引擎

        通过分析会话文件内容判断是 Claude、Codex 还是 Gemini

        Args:
            session_file: 会话文件路径

        Returns:
            引擎名称: "claude" | "codex" | "gemini" | None
        """
        try:
            with session_file.open("r", encoding="utf-8", errors="ignore") as f:
                # 读取前几行判断
                for _ in range(10):
                    line = f.readline().strip()
                    if not line:
                        break

                    try:
                        data = json.loads(line)

                        # 检查模型名称
                        model = data.get("model", "")
                        if model:
                            if "claude" in model.lower():
                                return "claude"
                            elif "gpt" in model.lower() or "codex" in model.lower():
                                return "codex"
                            elif "gemini" in model.lower():
                                return "gemini"

                        # 检查特定字段
                        if "anthropic" in str(data).lower():
                            return "claude"
                        elif "openai" in str(data).lower():
                            return "codex"
                        elif "google" in str(data).lower():
                            return "gemini"

                    except json.JSONDecodeError:
                        continue

        except OSError:
            pass

        # 默认返回 claude（因为文件在 ~/.claude/projects/ 下）
        return "claude"
