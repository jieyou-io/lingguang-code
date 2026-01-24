"""
项目文件服务
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app.core.errors import APIError
from app.schemas.project_files import FileNode


SKIP_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "__pycache__",
    ".tox",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
}


@dataclass(frozen=True)
class FileContentResult:
    path: str
    content: str
    truncated: bool
    size: int


class ProjectFileService:
    """项目文件扫描与读取服务"""

    def build_tree(
        self,
        project_path: str,
        max_depth: int = 4,
        max_files: int = 3000,
        include_hidden: bool = False,
    ) -> List[FileNode]:
        root = self._resolve_project_root(project_path)
        file_count = 0

        def sort_key(entry: Path) -> tuple[int, str]:
            return (0 if entry.is_dir() else 1, entry.name.lower())

        def walk(current: Path, depth: int) -> List[FileNode]:
            nonlocal file_count
            if depth > max_depth:
                return []
            try:
                entries = sorted(list(current.iterdir()), key=sort_key)
            except OSError:
                return []

            nodes: List[FileNode] = []
            for entry in entries:
                if file_count >= max_files:
                    break
                if entry.is_symlink():
                    continue
                if not include_hidden and entry.name.startswith("."):
                    continue
                if entry.is_dir() and entry.name in SKIP_DIRS:
                    continue

                try:
                    resolved = entry.resolve()
                    relative_path = resolved.relative_to(root)
                except (OSError, ValueError):
                    continue

                node_type = "folder" if entry.is_dir() else "file"
                extension = None
                size = None
                if node_type == "file":
                    extension = entry.suffix.lstrip(".").lower() or None
                    try:
                        size = entry.stat().st_size
                    except OSError:
                        size = None

                file_count += 1
                children = walk(entry, depth + 1) if node_type == "folder" else None
                nodes.append(
                    FileNode(
                        id=relative_path.as_posix(),
                        name=entry.name,
                        path=relative_path.as_posix(),
                        type=node_type,
                        children=children,
                        extension=extension,
                        size=size,
                    )
                )

            return nodes

        return walk(root, 0)

    def read_file_content(
        self,
        project_path: str,
        file_path: str,
        max_bytes: int = 200_000,
    ) -> FileContentResult:
        root = self._resolve_project_root(project_path)
        relative = Path(file_path)
        if relative.is_absolute():
            raise APIError(
                status_code=400,
                code="INVALID_PARAMETER",
                message="file_path 必须是相对路径",
            )

        try:
            resolved = (root / relative).resolve()
            resolved.relative_to(root)
        except (OSError, ValueError):
            raise APIError(
                status_code=400,
                code="INVALID_PARAMETER",
                message="file_path 超出项目范围",
            )

        if not resolved.exists() or not resolved.is_file():
            raise APIError(
                status_code=404,
                code="FILE_NOT_FOUND",
                message="文件不存在",
            )

        try:
            size = resolved.stat().st_size
        except OSError:
            size = 0

        try:
            with resolved.open("rb") as f:
                data = f.read(max_bytes + 1)
        except OSError as exc:
            raise APIError(
                status_code=500,
                code="READ_FAILED",
                message=f"读取文件失败: {exc}",
            )

        truncated = len(data) > max_bytes or size > max_bytes
        if len(data) > max_bytes:
            data = data[:max_bytes]

        content = data.decode("utf-8", errors="replace")

        return FileContentResult(
            path=relative.as_posix(),
            content=content,
            truncated=truncated,
            size=size,
        )

    def _resolve_project_root(self, project_path: str) -> Path:
        if not project_path:
            raise APIError(
                status_code=400,
                code="INVALID_PARAMETER",
                message="project_path 不能为空",
            )

        root = Path(project_path).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise APIError(
                status_code=404,
                code="PROJECT_NOT_FOUND",
                message="项目路径不存在",
                details=str(root),
            )

        return root
