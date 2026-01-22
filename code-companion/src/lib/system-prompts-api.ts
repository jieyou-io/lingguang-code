/**
 * 系统提示词管理 API 客户端
 */

import { get, put } from './api';

/**
 * 系统提示词响应
 */
export interface SystemPromptResponse {
  engine: string;
  content: string;
  file_path: string;
  exists: boolean;
}

/**
 * 系统提示词更新请求
 */
export interface SystemPromptUpdateRequest {
  content: string;
}

/**
 * 获取系统提示词
 *
 * @param engine 引擎名称 (claude, codex, gemini)
 * @returns 系统提示词内容
 */
export async function getSystemPrompt(engine: string): Promise<SystemPromptResponse> {
  return get<SystemPromptResponse>(`/v1/system-prompts/${engine}`);
}

/**
 * 更新系统提示词
 *
 * @param engine 引擎名称 (claude, codex, gemini)
 * @param content 新的提示词内容
 * @returns 更新后的系统提示词
 */
export async function updateSystemPrompt(
  engine: string,
  content: string
): Promise<SystemPromptResponse> {
  return put<SystemPromptResponse>(`/v1/system-prompts/${engine}`, { content });
}
