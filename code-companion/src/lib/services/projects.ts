/**
 * 项目相关 API
 */
import { get } from '../api';
import type { Project } from '@/types';

/**
 * 后端项目响应类型
 */
interface BackendProject {
  id: string;
  path: string;
  sessions: string[];
  created_at: number;
}

/**
 * 后端项目列表响应
 */
interface ProjectListResponse {
  projects: BackendProject[];
}

/**
 * 后端项目使用统计类型
 */
interface ProjectUsage {
  project_path: string;
  project_name: string;
  total_cost: number;
  total_tokens: number;
  session_count: number;
  last_used: string;
}

/**
 * 获取所有 Claude 项目
 */
export async function getClaudeProjects(): Promise<BackendProject[]> {
  const response = await get<ProjectListResponse>('/v1/projects/integrated');
  return response.projects || [];
}

/**
 * 获取项目使用统计
 */
export async function getProjectStats(): Promise<ProjectUsage[]> {
  const stats = await get<{ by_project: ProjectUsage[] }>('/v1/usage/stats');
  return stats.by_project || [];
}
