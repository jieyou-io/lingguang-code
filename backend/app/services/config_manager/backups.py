"""
配置文件备份管理模块

提供自动备份和旧备份清理功能。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Optional

import structlog

from app.core.errors import APIError

logger = structlog.get_logger()


class BackupManager:
    """
    配置文件备份管理器

    自动创建带时间戳的备份文件，并维护最新的 N 个备份。
    """

    def __init__(self, max_backups: int = 5) -> None:
        """
        初始化备份管理器

        Args:
            max_backups: 保留的最大备份数量，超过此数量的旧备份会被自动删除
        """
        self._max_backups = max_backups

    def backup(self, path: Path) -> Optional[Path]:
        """
        创建配置文件的备份

        Args:
            path: 需要备份的文件路径

        Returns:
            备份文件的路径，如果原文件不存在则返回 None

        Raises:
            APIError: 备份失败时抛出
        """
        if not path.exists():
            logger.debug("backup_skipped_file_not_exists", path=str(path))
            return None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = path.with_name(f"{path.name}.bak.{timestamp}")

        try:
            # 使用 shutil.copy2 保留文件元数据（权限、时间戳等）
            shutil.copy2(path, backup_path)
            logger.info("config_backup_created", original=str(path), backup=str(backup_path))

            # 清理旧备份
            self._prune_backups(path)

        except OSError as exc:
            logger.warning("config_backup_failed", path=str(path), error=str(exc))
            raise APIError(
                status_code=500,
                code="CONFIG_BACKUP_FAILED",
                message="配置文件备份失败",
                details=str(exc),
            ) from exc

        return backup_path

    def _prune_backups(self, original_path: Path) -> None:
        """
        清理旧备份文件，保留最新的 max_backups 个

        Args:
            original_path: 原始文件路径，用于查找相关备份文件
        """
        pattern = f"{original_path.name}.bak."
        backups = []

        # 查找所有备份文件
        for item in original_path.parent.iterdir():
            if item.is_file() and item.name.startswith(pattern):
                backups.append(item)

        # 按文件名排序（时间戳在文件名中，所以字符串排序即可）
        backups.sort(key=lambda p: p.name, reverse=True)

        # 删除超出限制的旧备份
        if len(backups) <= self._max_backups:
            return

        for old_backup in backups[self._max_backups:]:
            try:
                old_backup.unlink()
                logger.debug("old_backup_pruned", path=str(old_backup))
            except OSError as exc:
                logger.warning("backup_prune_failed", path=str(old_backup), error=str(exc))
