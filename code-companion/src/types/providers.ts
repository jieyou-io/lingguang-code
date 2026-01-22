/**
 * Provider 配置相关类型定义
 */

/**
 * Claude 引擎当前配置
 */
export interface ClaudeCurrentConfig {
  env?: Record<string, string>;
  apiKeyHelper?: string;
}

/**
 * Codex 引擎当前配置
 */
export interface CodexCurrentConfig {
  auth?: Record<string, any>;
  config?: Record<string, any>;
}

/**
 * Gemini 引擎当前配置
 */
export interface GeminiCurrentConfig {
  env?: Record<string, string>;
  settings?: Record<string, any>;
}

/**
 * Provider 当前配置联合类型
 */
export type ProviderCurrentConfig = ClaudeCurrentConfig | CodexCurrentConfig | GeminiCurrentConfig;

/**
 * Provider 配置响应
 */
export interface ProviderConfigResponse {
  engine: string;
  config: ProviderCurrentConfig;
}

/**
 * Provider 配置更新请求
 */
export interface ProviderConfigUpdateRequest {
  apiKey?: string | null;
  baseUrl?: string | null;
  enabled?: boolean | null;
  model?: string | null;
  temperature?: number | null;
}

/**
 * Provider 预设
 */
export interface ProviderPreset {
  id: string;
  name: string;
  description?: string;
  config: Record<string, any>;
}

/**
 * Provider 预设响应
 */
export interface ProviderPresetResponse {
  id: string;
  name: string;
  description?: string;
  config: Record<string, any>;
}

/**
 * Provider 预设创建请求
 */
export interface ProviderPresetCreateRequest {
  id: string;
  name: string;
  description?: string;
  config: Record<string, any>;
}
