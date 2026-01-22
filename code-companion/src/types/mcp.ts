/**
 * MCP 相关类型定义
 */

/**
 * MCP 引擎类型
 */
export type MCPEngine = 'claude' | 'codex' | 'gemini';

/**
 * MCP 传输协议
 */
export type MCPTransport = 'stdio' | 'sse';

/**
 * MCP 服务器状态
 */
export interface MCPServerStatus {
  running: boolean;
  error?: string | null;
  lastChecked?: number | null;
}

/**
 * MCP 服务器配置
 */
export interface MCPServer {
  id: string;
  name: string;
  transport: MCPTransport;
  command?: string | null;
  args: string[];
  env: Record<string, string>;
  url?: string | null;
  scope: string;
  isActive: boolean;
  status: MCPServerStatus;
}

/**
 * MCP 服务器列表响应
 */
export interface MCPListResponse {
  servers: MCPServer[];
}

/**
 * MCP 测试响应
 */
export interface MCPTestResponse {
  id: string;
  status: string;
  detail?: string | null;
}

/**
 * MCP 创建请求
 */
export interface MCPCreateRequest {
  name: string;
  transport: MCPTransport;
  command?: string | null;
  args?: string[];
  env?: Record<string, string>;
  url?: string | null;
  scope?: string;
  isActive?: boolean;
}

/**
 * MCP 更新请求
 */
export interface MCPUpdateRequest {
  name?: string;
  transport?: MCPTransport;
  command?: string | null;
  args?: string[];
  env?: Record<string, string>;
  url?: string | null;
  scope?: string;
  isActive?: boolean;
}

/**
 * MCP 启动响应
 */
export interface MCPStartResponse {
  success: boolean;
  message?: string;
}

/**
 * MCP 停止响应
 */
export interface MCPStopResponse {
  success: boolean;
  message?: string;
}
