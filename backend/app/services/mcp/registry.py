"""
MCP 服务器注册表
"""
from typing import Dict, Optional


class MCPRegistry:
    """MCP 服务器状态缓存"""

    def __init__(self) -> None:
        self._status: Dict[str, dict] = {}

    def set_status(self, server_id: str, status: dict) -> None:
        self._status[server_id] = status

    def get_status(self, server_id: str) -> Optional[dict]:
        return self._status.get(server_id)


mcp_registry = MCPRegistry()
