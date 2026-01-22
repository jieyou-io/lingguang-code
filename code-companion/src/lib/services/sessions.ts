/**
 * 会话相关 API
 */
import { get, del } from '../api';

/**
 * 后端会话响应类型
 */
export interface BackendSession {
  id: string;
  project_id: string;
  project_path: string;
  created_at: number;
  first_message?: string | null;
  message_timestamp?: string | null;
  last_message_timestamp?: string | null;
  model?: string | null;
  engine?: string;
}

/**
 * 会话列表响应
 */
export interface SessionListResponse {
  sessions: BackendSession[];
}

/**
 * 获取项目的所有会话
 */
export async function getProjectSessions(projectId: string): Promise<BackendSession[]> {
  const response = await get<SessionListResponse>(`/v1/projects/${projectId}/sessions`);
  return response.sessions || [];
}

/**
 * 删除 Claude 会话
 */
export async function deleteClaudeSession(projectId: string, sessionId: string): Promise<void> {
  await del(`/v1/sessions/claude/${projectId}/${sessionId}`);
}

/**
 * 获取 Claude 会话历史消息
 */
export async function getClaudeSessionHistory(projectId: string, sessionId: string): Promise<any> {
  return get(`/v1/sessions/claude/${projectId}/${sessionId}/history`);
}

/**
 * 获取 Codex 会话历史消息
 */
export async function getCodexSessionHistory(sessionId: string): Promise<any> {
  return get(`/v1/sessions/codex/${sessionId}/history`);
}

/**
 * 获取 Gemini 会话历史消息
 */
export async function getGeminiSessionHistory(sessionId: string): Promise<any> {
  return get(`/v1/sessions/gemini/${sessionId}/history`);
}

