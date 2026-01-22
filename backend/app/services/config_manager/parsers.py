"""
配置文件解析器模块

支持多种配置文件格式的读写：JSON、TOML、YAML、Markdown with Frontmatter。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple
import json

import structlog

from app.core.errors import APIError

logger = structlog.get_logger()


class ConfigParsers:
    """
    配置文件解析器

    提供统一的接口来解析和序列化不同格式的配置文件。
    """

    def read_json(self, path: Path) -> Dict[str, Any]:
        """
        读取 JSON 配置文件

        Args:
            path: JSON 文件路径

        Returns:
            解析后的字典数据

        Raises:
            APIError: 文件不存在或解析失败时抛出
        """
        if not path.exists():
            raise APIError(
                status_code=404,
                code="CONFIG_NOT_FOUND",
                message="配置文件不存在",
                details=str(path),
            )

        try:
            content = path.read_text(encoding="utf-8")
            return json.loads(content)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("config_json_read_failed", path=str(path), error=str(exc))
            raise APIError(
                status_code=400,
                code="CONFIG_PARSE_ERROR",
                message="JSON 配置文件解析失败",
                details=str(exc),
            ) from exc

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        """
        写入 JSON 配置文件

        Args:
            path: JSON 文件路径
            data: 要写入的字典数据

        Raises:
            APIError: 写入失败时抛出
        """
        try:
            # ensure_ascii=False 以支持中文等非 ASCII 字符
            content = json.dumps(data, ensure_ascii=False, indent=2)
            path.write_text(content, encoding="utf-8")
        except (OSError, TypeError) as exc:
            logger.warning("config_json_write_failed", path=str(path), error=str(exc))
            raise APIError(
                status_code=500,
                code="CONFIG_WRITE_ERROR",
                message="JSON 配置文件写入失败",
                details=str(exc),
            ) from exc

    def read_toml(self, path: Path) -> Dict[str, Any]:
        """
        读取 TOML 配置文件

        Args:
            path: TOML 文件路径

        Returns:
            解析后的字典数据

        Raises:
            APIError: 文件不存在、TOML 不可用或解析失败时抛出
        """
        if not path.exists():
            raise APIError(
                status_code=404,
                code="CONFIG_NOT_FOUND",
                message="配置文件不存在",
                details=str(path),
            )

        try:
            import tomllib
        except ImportError as exc:
            raise APIError(
                status_code=500,
                code="TOML_UNAVAILABLE",
                message="TOML 解析器不可用（需要 Python 3.11+）",
                details=str(exc),
            ) from exc

        try:
            content = path.read_text(encoding="utf-8")
            return tomllib.loads(content)
        except (OSError, ValueError) as exc:
            logger.warning("config_toml_read_failed", path=str(path), error=str(exc))
            raise APIError(
                status_code=400,
                code="CONFIG_PARSE_ERROR",
                message="TOML 配置文件解析失败",
                details=str(exc),
            ) from exc

    def write_toml(self, path: Path, data: Dict[str, Any]) -> None:
        """
        写入 TOML 配置文件

        Args:
            path: TOML 文件路径
            data: 要写入的字典数据

        Raises:
            APIError: TOML 写入库不可用或写入失败时抛出
        """
        try:
            import tomli_w
        except ImportError as exc:
            raise APIError(
                status_code=500,
                code="TOML_WRITER_UNAVAILABLE",
                message="TOML 写入库不可用（需要安装 tomli_w）",
                details=str(exc),
            ) from exc

        try:
            content = tomli_w.dumps(data)
            path.write_text(content, encoding="utf-8")
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("config_toml_write_failed", path=str(path), error=str(exc))
            raise APIError(
                status_code=500,
                code="CONFIG_WRITE_ERROR",
                message="TOML 配置文件写入失败",
                details=str(exc),
            ) from exc

    def read_markdown_frontmatter(self, path: Path) -> Tuple[Dict[str, Any], str]:
        """
        读取带 YAML frontmatter 的 Markdown 文件

        Args:
            path: Markdown 文件路径

        Returns:
            元组 (metadata, content)，其中 metadata 是 YAML 元数据字典，
            content 是 Markdown 正文内容

        Raises:
            APIError: 文件不存在、frontmatter 不可用或解析失败时抛出
        """
        if not path.exists():
            raise APIError(
                status_code=404,
                code="CONFIG_NOT_FOUND",
                message="配置文件不存在",
                details=str(path),
            )

        try:
            import frontmatter
        except ImportError as exc:
            raise APIError(
                status_code=500,
                code="FRONTMATTER_UNAVAILABLE",
                message="Frontmatter 解析器不可用（需要安装 python-frontmatter）",
                details=str(exc),
            ) from exc

        try:
            post = frontmatter.load(path)
            return dict(post.metadata), post.content
        except (OSError, ValueError) as exc:
            logger.warning("config_markdown_read_failed", path=str(path), error=str(exc))
            raise APIError(
                status_code=400,
                code="CONFIG_PARSE_ERROR",
                message="Markdown frontmatter 解析失败",
                details=str(exc),
            ) from exc

    def write_markdown_frontmatter(
        self, path: Path, metadata: Dict[str, Any], content: str
    ) -> None:
        """
        写入带 YAML frontmatter 的 Markdown 文件

        Args:
            path: Markdown 文件路径
            metadata: YAML 元数据字典
            content: Markdown 正文内容

        Raises:
            APIError: frontmatter 不可用或写入失败时抛出
        """
        try:
            import frontmatter
        except ImportError as exc:
            raise APIError(
                status_code=500,
                code="FRONTMATTER_UNAVAILABLE",
                message="Frontmatter 写入库不可用（需要安装 python-frontmatter）",
                details=str(exc),
            ) from exc

        try:
            post = frontmatter.Post(content, **metadata)
            path.write_text(frontmatter.dumps(post), encoding="utf-8")
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("config_markdown_write_failed", path=str(path), error=str(exc))
            raise APIError(
                status_code=500,
                code="CONFIG_WRITE_ERROR",
                message="Markdown frontmatter 写入失败",
                details=str(exc),
            ) from exc
