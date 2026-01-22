/**
 * MCP 相关 API
 */
import { get, post, put, del } from '../api';
import type {
  MCPEngine,
  MCPListResponse,
  MCPServer,
  MCPTestResponse,
  MCPCreateRequest,
  MCPUpdateRequest,
  MCPStartResponse,
  MCPStopResponse,
} from '@/types/mcp';

/**
 * 获取指定引擎的 MCP 服务器列表
 */
export async function getMCPServers(engine: MCPEngine): Promise<MCPListResponse> {
  return get<MCPListResponse>(`/v1/mcp/engines/${engine}/servers`);
}

/**
 * 测试 MCP 服务器连接
 */
export async function testMCPServer(
  engine: MCPEngine,
  serverId: string
): Promise<MCPTestResponse> {
  return post<MCPTestResponse>(`/v1/mcp/engines/${engine}/servers/${serverId}/test`);
}

/**
 * 创建 MCP 服务器
 */
export async function createMCPServer(
  engine: MCPEngine,
  data: MCPCreateRequest
): Promise<MCPServer> {
  return post<MCPServer>(`/v1/mcp/engines/${engine}/servers`, data);
}

/**
 * 更新 MCP 服务器
 */
export async function updateMCPServer(
  engine: MCPEngine,
  serverId: string,
  data: MCPUpdateRequest
): Promise<MCPServer> {
  return put<MCPServer>(`/v1/mcp/engines/${engine}/servers/${serverId}`, data);
}

/**
 * 删除 MCP 服务器
 */
export async function deleteMCPServer(
  engine: MCPEngine,
  serverId: string
): Promise<{ success: boolean }> {
  return del<{ success: boolean }>(`/v1/mcp/engines/${engine}/servers/${serverId}`);
}

/**
 * 启动 MCP 服务器
 */
export async function startMCPServer(
  engine: MCPEngine,
  serverId: string
): Promise<MCPStartResponse> {
  return post<MCPStartResponse>(`/v1/mcp/engines/${engine}/servers/${serverId}/start`);
}

/**
 * 停止 MCP 服务器
 */
export async function stopMCPServer(
  engine: MCPEngine,
  serverId: string
): Promise<MCPStopResponse> {
  return post<MCPStopResponse>(`/v1/mcp/engines/${engine}/servers/${serverId}/stop`);
}
