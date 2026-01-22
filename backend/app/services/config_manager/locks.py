"""
文件锁工具模块

提供基于 filelock 的文件锁机制，支持超时和 fallback。
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from threading import Lock
import time
from typing import ContextManager, Dict, Iterator

import structlog

from app.core.errors import APIError

logger = structlog.get_logger()

try:
    from filelock import FileLock, Timeout
    FILELOCK_AVAILABLE = True
except ImportError:
    FileLock = None
    Timeout = Exception
    FILELOCK_AVAILABLE = False
    logger.warning("filelock_not_available", message="filelock库未安装，将使用线程锁作为fallback")


class FileLockProvider:
    """
    文件锁提供者

    提供基于文件系统的锁机制，用于防止并发写入配置文件时的冲突。
    如果 filelock 库不可用，会自动降级为线程锁（仅限单进程环境）。
    """

    def __init__(self, timeout_seconds: float = 5.0, poll_interval: float = 0.1) -> None:
        """
        初始化文件锁提供者

        Args:
            timeout_seconds: 获取锁的超时时间（秒）
            poll_interval: fallback 模式下的轮询间隔（秒）
        """
        self._timeout_seconds = timeout_seconds
        self._poll_interval = poll_interval
        self._fallback_locks: Dict[str, Lock] = {}

    def lock(self, path: Path) -> ContextManager[None]:
        """
        获取指定文件路径的锁

        Args:
            path: 需要锁定的文件路径

        Returns:
            上下文管理器，用于 with 语句

        Raises:
            APIError: 获取锁失败或超时时抛出
        """
        if FILELOCK_AVAILABLE:
            return self._filelock(path)
        return self._fallback_lock(path)

    @contextmanager
    def _filelock(self, path: Path) -> Iterator[None]:
        """使用 filelock 库实现的跨进程文件锁"""
        lock_path = path.with_name(f".{path.name}.lock")
        lock = FileLock(str(lock_path), timeout=self._timeout_seconds)

        try:
            lock.acquire(timeout=self._timeout_seconds)
        except Timeout as exc:
            raise APIError(
                status_code=409,
                code="CONFIG_LOCK_TIMEOUT",
                message="配置文件锁定超时，请稍后重试",
                details=f"Failed to acquire lock for {path}: {exc}",
            ) from exc
        except OSError as exc:
            logger.warning("config_lock_failed", path=str(path), error=str(exc))
            raise APIError(
                status_code=500,
                code="CONFIG_LOCK_FAILED",
                message="无法获取配置文件锁",
                details=str(exc),
            ) from exc

        try:
            yield
        finally:
            try:
                lock.release()
            except OSError as exc:
                logger.warning("config_lock_release_failed", path=str(path), error=str(exc))

    @contextmanager
    def _fallback_lock(self, path: Path) -> Iterator[None]:
        """Fallback 线程锁实现（仅限单进程环境）"""
        key = str(path.resolve())
        lock = self._fallback_locks.setdefault(key, Lock())

        deadline = time.monotonic() + self._timeout_seconds
        acquired = False

        while time.monotonic() < deadline:
            acquired = lock.acquire(blocking=False)
            if acquired:
                break
            time.sleep(self._poll_interval)

        if not acquired:
            raise APIError(
                status_code=409,
                code="CONFIG_LOCK_TIMEOUT",
                message="配置文件锁定超时，请稍后重试",
                details=f"Fallback lock timeout for {path}",
            )

        try:
            yield
        finally:
            lock.release()
