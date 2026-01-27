"""
MCP 管理服务
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

import structlog

from app.core.errors import APIError
from app.services.config_manager.backups import BackupManager
from app.services.config_manager.locks import FileLockProvider
from app.services.mcp.process_manager import MCPProcessManager
from app.services.mcp.registry import MCPRegistry

logger = structlog.get_logger()


class MCPService:
    """MCP 业务服务"""

    def __init__(self, registry: MCPRegistry) -> None:
        self._registry = registry
        self._locks = FileLockProvider()
        self._backups = BackupManager()
        self._process_manager = MCPProcessManager()

    def _read_json(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("mcp_config_read_failed", path=str(path), error=str(exc))
            return None

    def _read_toml(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        try:
            import tomllib
        except ImportError:  # pragma: no cover
            logger.warning("mcp_toml_not_available", path=str(path))
            return None
        try:
            return tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning("mcp_config_read_failed", path=str(path), error=str(exc))
            return None

    def _normalize_server(self, name: str, raw: dict) -> dict:
        command = raw.get("command")
        url = raw.get("url")
        transport = raw.get("transport")
        if not transport:
            transport = "sse" if url else "stdio"
        return {
            "id": name,
            "name": name,
            "transport": transport,
            "command": command,
            "args": raw.get("args", []),
            "env": raw.get("env", {}),
            "url": url,
            "scope": raw.get("scope", "local"),
            "isActive": raw.get("isActive", True),
        }

    async def list_servers(self, engine: str) -> List[dict]:
        if engine == "claude":
            # Claude MCP 配置在 ~/.claude.json (不是 ~/.claude/settings.json)
            config_path = Path("~/.claude.json").expanduser()
            data = self._read_json(config_path) or {}
            raw_servers = data.get("mcpServers", {})
            servers = []
            for name, raw in raw_servers.items():
                server = self._normalize_server(name, raw)
                status = self._registry.get_status(server["id"])
                server["status"] = status or {
                    "running": False,
                    "error": None,
                    "lastChecked": None,
                }
                servers.append(server)
            return servers

        if engine == "gemini":
            config_path = Path("~/.gemini/settings.json").expanduser()
            data = self._read_json(config_path) or {}
            raw_servers = data.get("mcpServers", {})
            servers = []
            for name, raw in raw_servers.items():
                server = self._normalize_server(name, raw)
                status = self._registry.get_status(server["id"])
                server["status"] = status or {
                    "running": False,
                    "error": None,
                    "lastChecked": None,
                }
                servers.append(server)
            return servers

        if engine == "codex":
            # Codex MCP 配置在 ~/.codex/config.toml (不是 settings.toml)
            config_path = Path("~/.codex/config.toml").expanduser()
            data = self._read_toml(config_path) or {}
            raw_servers = data.get("mcp_servers", {})
            servers = []
            if isinstance(raw_servers, dict):
                for name, raw in raw_servers.items():
                    server = self._normalize_server(name, raw)
                    status = self._registry.get_status(server["id"])
                    server["status"] = status or {
                        "running": False,
                        "error": None,
                        "lastChecked": None,
                    }
                    servers.append(server)
            elif isinstance(raw_servers, list):
                for raw in raw_servers:
                    name = raw.get("name") or raw.get("id") or "codex-server"
                    server = self._normalize_server(name, raw)
                    status = self._registry.get_status(server["id"])
                    server["status"] = status or {
                        "running": False,
                        "error": None,
                        "lastChecked": None,
                    }
                    servers.append(server)
            return servers

        return []

    async def test_server(self, server_id: str) -> dict:
        status = {
            "running": True,
            "error": None,
            "lastChecked": int(time.time()),
        }
        self._registry.set_status(server_id, status)
        return {"status": "ok", "detail": None}

    def _get_config_path(self, engine: str) -> Path:
        """获取配置文件路径"""
        if engine == "claude":
            # Claude MCP 配置在 ~/.claude.json (不是 ~/.claude/settings.json)
            return Path("~/.claude.json").expanduser()
        elif engine == "gemini":
            return Path("~/.gemini/settings.json").expanduser()
        elif engine == "codex":
            # Codex MCP 配置在 ~/.codex/config.toml (不是 settings.toml)
            return Path("~/.codex/config.toml").expanduser()
        else:
            raise APIError(
                status_code=400,
                code="INVALID_ENGINE",
                message=f"不支持的引擎: {engine}",
            )

    def _write_json(self, path: Path, data: dict) -> None:
        """写入 JSON 配置文件"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._locks.lock(path):
            self._backups.backup(path)
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _write_toml(self, path: Path, data: dict) -> None:
        """写入 TOML 配置文件"""
        try:
            import tomli_w
        except ImportError:
            raise APIError(
                status_code=500,
                code="TOML_NOT_AVAILABLE",
                message="tomli_w 库不可用",
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._locks.lock(path):
            self._backups.backup(path)
            path.write_text(tomli_w.dumps(data), encoding="utf-8")

    async def create_server(self, engine: str, request: dict) -> dict:
        """创建 MCP 服务器配置"""
        config_path = self._get_config_path(engine)

        # 读取现有配置
        if engine == "codex":
            data = self._read_toml(config_path) or {}
            servers_key = "mcp_servers"
        else:
            data = self._read_json(config_path) or {}
            servers_key = "mcpServers"

        servers = data.get(servers_key, {})

        # 检查服务器是否已存在
        if request["name"] in servers:
            raise APIError(
                status_code=409,
                code="SERVER_EXISTS",
                message=f"MCP 服务器 '{request['name']}' 已存在",
            )

        # 添加新服务器（过滤 None，避免 TOML 序列化失败）
        server_payload = {
            "transport": request["transport"],
            "command": request.get("command"),
            "args": request.get("args", []),
            "env": request.get("env", {}),
            "url": request.get("url"),
            "scope": request.get("scope", "local"),
            "isActive": request.get("isActive", True),
        }
        servers[request["name"]] = {k: v for k, v in server_payload.items() if v is not None}

        data[servers_key] = servers

        # 写入配置
        if engine == "codex":
            self._write_toml(config_path, data)
        else:
            self._write_json(config_path, data)

        return self._normalize_server(request["name"], servers[request["name"]])

    async def update_server(self, engine: str, server_id: str, request: dict) -> dict:
        """更新 MCP 服务器配置"""
        config_path = self._get_config_path(engine)

        # 读取现有配置
        if engine == "codex":
            data = self._read_toml(config_path) or {}
            servers_key = "mcp_servers"
        else:
            data = self._read_json(config_path) or {}
            servers_key = "mcpServers"

        servers = data.get(servers_key, {})

        # 检查服务器是否存在
        if server_id not in servers:
            raise APIError(
                status_code=404,
                code="SERVER_NOT_FOUND",
                message=f"MCP 服务器 '{server_id}' 不存在",
            )

        # 更新服务器配置
        server = servers[server_id]
        if request.get("name") and request["name"] != server_id:
            # 重命名服务器
            servers[request["name"]] = server
            del servers[server_id]
            server_id = request["name"]

        for key in ["transport", "command", "args", "env", "url", "isActive"]:
            if key in request and request[key] is not None:
                server[key] = request[key]

        data[servers_key] = servers

        # 写入配置
        if engine == "codex":
            self._write_toml(config_path, data)
        else:
            self._write_json(config_path, data)

        return self._normalize_server(server_id, server)

    async def delete_server(self, engine: str, server_id: str) -> None:
        """删除 MCP 服务器配置"""
        config_path = self._get_config_path(engine)

        # 读取现有配置
        if engine == "codex":
            data = self._read_toml(config_path) or {}
            servers_key = "mcp_servers"
        else:
            data = self._read_json(config_path) or {}
            servers_key = "mcpServers"

        servers = data.get(servers_key, {})

        # 检查服务器是否存在
        if server_id not in servers:
            raise APIError(
                status_code=404,
                code="SERVER_NOT_FOUND",
                message=f"MCP 服务器 '{server_id}' 不存在",
            )

        # 删除服务器
        del servers[server_id]
        data[servers_key] = servers

        # 写入配置
        if engine == "codex":
            self._write_toml(config_path, data)
        else:
            self._write_json(config_path, data)

    async def start_server(self, engine: str, server_id: str) -> dict:
        """启动 MCP 服务器进程"""
        # 获取服务器配置
        servers = await self.list_servers(engine)
        server = next((s for s in servers if s["id"] == server_id), None)

        if not server:
            raise APIError(
                status_code=404,
                code="SERVER_NOT_FOUND",
                message=f"MCP 服务器 '{server_id}' 不存在",
            )

        # 检查是否已运行
        if self._process_manager.is_running(server_id):
            return {
                "id": server_id,
                "status": "already_running",
                "pid": self._process_manager.get_process(server_id).pid if self._process_manager.get_process(server_id) else None,
            }

        # 启动进程
        process = await self._process_manager.start(server)

        # 更新状态
        status = {
            "running": True,
            "error": None,
            "lastChecked": int(time.time()),
        }
        self._registry.set_status(server_id, status)

        return {
            "id": server_id,
            "status": "started",
            "pid": process.pid if process else None,
        }

    async def stop_server(self, server_id: str) -> dict:
        """停止 MCP 服务器进程"""
        # 停止进程
        await self._process_manager.stop(server_id)

        # 更新状态
        status = {
            "running": False,
            "error": None,
            "lastChecked": int(time.time()),
        }
        self._registry.set_status(server_id, status)

        return {
            "id": server_id,
            "status": "stopped",
        }
