/**
 * Usage 统计 API 客户端
 */

import { get } from './api';

/**
 * 快速统计单项数据
 */
export interface QuickStatsItem {
  tokens: number;
  cost: number;
  sessions: number;
}

/**
 * 快速统计响应 - 专为会话页面和项目页面设计
 */
export interface QuickStatsResponse {
  today: QuickStatsItem;
  week: QuickStatsItem;
  month: QuickStatsItem;
}

/**
 * 按模型统计
 */
export interface ModelUsage {
  model: string;
  total_cost: number;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  session_count: number;
}

/**
 * 按日期统计
 */
export interface DailyUsage {
  date: string;
  total_cost: number;
  total_tokens: number;
  models_used: string[];
}

/**
 * 按项目统计
 */
export interface ProjectUsage {
  project_path: string;
  project_name: string;
  total_cost: number;
  total_tokens: number;
  session_count: number;
  last_used: string;
}

/**
 * 使用统计响应
 */
export interface UsageStatsResponse {
  total_cost: number;
  total_tokens: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cache_creation_tokens: number;
  total_cache_read_tokens: number;
  total_sessions: number;
  by_model: ModelUsage[];
  by_date: DailyUsage[];
  by_project: ProjectUsage[];
  by_engine: {
    claude: number;
    codex: number;
    gemini: number;
  };
}

/**
 * 获取快速统计
 *
 * @param projectPath 项目路径，不传则统计所有项目
 * @returns 今日/本周/本月的快速统计数据
 */
export async function getQuickStats(projectPath?: string): Promise<QuickStatsResponse> {
  const params = projectPath ? `?project_path=${encodeURIComponent(projectPath)}` : '';
  return get<QuickStatsResponse>(`/v1/usage/quick-stats${params}`);
}

/**
 * 获取完整使用统计
 *
 * @param days 统计最近 N 天的数据，不传则统计全部
 * @returns 完整的使用统计数据
 */
export async function getUsageStats(days?: number): Promise<UsageStatsResponse> {
  const params = days ? `?days=${days}` : '';
  return get<UsageStatsResponse>(`/v1/usage/stats${params}`);
}
