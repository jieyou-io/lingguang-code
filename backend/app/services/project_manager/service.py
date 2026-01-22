"""
项目管理服务

提供项目扫描、集成项目查询和对比功能。
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import structlog

from app.core.errors import APIError
from app.services.project_manager.claude_project_scanner import ClaudeProjectScanner
from app.services.project_manager.session_scanner import CodexSessionScanner, GeminiSessionScanner

logger = structlog.get_logger()


class ProjectManagerService:
    """
    项目管理服务

    提供以下功能：
    1. 从数据库查询已集成项目（使用过 Claude/Codex/Gemini 的项目）
    2. 扫描文件系统查找 Git 项目
    3. 对比集成项目和扫描项目的差异
    """

    def __init__(self) -> None:
        """初始化项目管理服务"""
        self._claude_scanner = ClaudeProjectScanner()

    async def list_integrated_projects(self) -> List[Dict]:
        """
        查询所有已集成项目

        从 ~/.claude/projects/ 目录扫描所有使用过 Claude CLI 的项目。

        Returns:
            项目列表，每个项目包含：
            - id: 项目 ID（目录名）
            - path: 项目路径
            - sessions: 会话 ID 列表
            - created_at: 最后活跃时间（Unix 时间戳）
        """
        # 使用 Claude 项目扫描器从文件系统获取项目
        projects = self._claude_scanner.list_projects()
        return projects

    def get_project_sessions(self, project_id: str) -> List[Dict]:
        """
        获取指定项目的所有会话详情

        Args:
            project_id: 项目 ID（目录名）

        Returns:
            会话列表
        """
        claude_sessions = self._claude_scanner.get_project_sessions(project_id)
        project_path = self._extract_project_path(project_id, claude_sessions)

        codex_sessions: List[Dict] = []
        gemini_sessions: List[Dict] = []

        if project_path:
            codex_scanner = CodexSessionScanner()
            gemini_scanner = GeminiSessionScanner()

            codex_sessions = [
                session
                for session in codex_scanner.list_sessions()
                if self._normalize_path(session.get("projectPath")) == self._normalize_path(project_path)
            ]
            gemini_sessions = gemini_scanner.list_sessions(project_path=project_path)

            for session in codex_sessions:
                session.setdefault("project_id", project_id)
                session.setdefault("project_path", project_path)
            for session in gemini_sessions:
                session.setdefault("project_id", project_id)
                session.setdefault("project_path", project_path)

        all_sessions = [*claude_sessions, *codex_sessions, *gemini_sessions]
        all_sessions.sort(key=self._session_sort_key, reverse=True)
        return all_sessions

    def _extract_project_path(self, project_id: str, sessions: List[Dict]) -> Optional[str]:
        if sessions:
            project_path = sessions[0].get("project_path") or sessions[0].get("projectPath")
            if project_path:
                return project_path
        return self._decode_project_id(project_id)

    def _decode_project_id(self, project_id: str) -> Optional[str]:
        if not project_id:
            return None
        if "--" in project_id:
            placeholder = "\x00"
            return project_id.replace("--", placeholder).replace("-", "/").replace(placeholder, "-")
        return project_id.replace("-", "/")

    def _normalize_path(self, path: Optional[str]) -> str:
        if not path:
            return ""
        return path.rstrip("/").lower()

    def _session_sort_key(self, session: Dict) -> float:
        from datetime import datetime

        timestamp = session.get("last_message_timestamp") or session.get("message_timestamp")
        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
            except ValueError:
                pass

        created_at = session.get("created_at")
        if isinstance(created_at, (int, float)):
            return float(created_at)
        return 0.0

    def scan_projects(self, roots: Iterable[Path], max_depth: int = 6) -> List[str]:
        """
        扫描文件系统查找 Git 项目

        Args:
            roots: 要扫描的根目录列表
            max_depth: 最大扫描深度（默认 6 层）

        Returns:
            Git 项目路径列表（已去重和排序）

        Raises:
            APIError: max_depth 参数无效时抛出
        """
        if max_depth < 1:
            raise APIError(
                status_code=400,
                code="INVALID_PARAMETER",
                message="max_depth 必须 >= 1",
            )

        projects: Set[str] = set()

        for root in roots:
            root_path = root.expanduser().resolve()
            if not root_path.exists():
                logger.warning("project_root_missing", path=str(root_path))
                continue

            projects.update(self._scan_root(root_path, max_depth))

        return sorted(projects)

    def compare_projects(self, integrated: List[str], scanned: List[str]) -> Dict[str, List[str]]:
        """
        对比已集成项目和扫描项目

        Args:
            integrated: 已集成项目列表
            scanned: 扫描到的项目列表

        Returns:
            字典包含以下字段：
            - integrated: 所有已集成项目（规范化路径）
            - scanned: 所有扫描到的项目（规范化路径）
            - unintegrated: 扫描到但未集成的项目
            - missingOnDisk: 已集成但磁盘上不存在的项目
        """
        # 规范化路径（展开用户目录和符号链接）
        integrated_set = {str(Path(p).expanduser().resolve()) for p in integrated}
        scanned_set = {str(Path(p).expanduser().resolve()) for p in scanned}

        return {
            "integrated": sorted(integrated_set),
            "scanned": sorted(scanned_set),
            "unintegrated": sorted(scanned_set - integrated_set),
            "missingOnDisk": sorted(integrated_set - scanned_set),
        }

    def _scan_root(self, root: Path, max_depth: int) -> Set[str]:
        """
        递归扫描单个根目录查找 Git 项目

        使用广度优先搜索（BFS）以控制深度。

        Args:
            root: 根目录路径
            max_depth: 最大扫描深度

        Returns:
            找到的 Git 项目路径集合
        """
        projects: Set[str] = set()
        queue = deque([(root, 0)])  # (当前路径, 当前深度)

        while queue:
            current, depth = queue.popleft()

            # 超过最大深度则跳过
            if depth > max_depth:
                continue

            # 读取当前目录的所有条目
            try:
                entries = list(current.iterdir())
            except OSError as exc:
                logger.warning("project_scan_failed", path=str(current), error=str(exc))
                continue

            # 检查是否包含 .git 目录（表示是 Git 项目）
            has_git = False
            for entry in entries:
                if entry.is_dir() and entry.name == ".git":
                    projects.add(str(current))
                    has_git = True
                    break

            # 如果当前目录是 Git 项目，则不再递归其子目录
            # （避免扫描 Git 仓库内的子模块）
            if has_git:
                continue

            # 递归扫描子目录（跳过常见的大型目录）
            for entry in entries:
                if entry.is_dir() and entry.name not in {
                    ".git",
                    ".venv",
                    "venv",
                    "node_modules",
                    "__pycache__",
                    ".tox",
                    ".pytest_cache",
                    "dist",
                    "build",
                }:
                    queue.append((entry, depth + 1))

        return projects
