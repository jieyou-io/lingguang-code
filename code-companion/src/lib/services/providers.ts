/**
 * Provider 配置相关 API
 */
import { get, put, post, del } from '../api';
import type {
  ProviderConfigResponse,
  ProviderConfigUpdateRequest,
  ProviderPresetResponse,
  ProviderPresetCreateRequest,
} from '@/types/providers';

/**
 * 获取指定引擎的当前 Provider 配置
 */
export async function getProviderConfig(engine: string): Promise<ProviderConfigResponse> {
  return get<ProviderConfigResponse>(`/v1/providers/${engine}`);
}

/**
 * 获取指定引擎的 Provider 预设列表
 */
export async function getProviderPresets(engine: string): Promise<ProviderPresetResponse[]> {
  return get<ProviderPresetResponse[]>(`/v1/providers/${engine}/presets`);
}

/**
 * 创建 Provider 预设
 */
export async function createProviderPreset(
  engine: string,
  preset: ProviderPresetCreateRequest
): Promise<ProviderPresetResponse> {
  return post<ProviderPresetResponse>(`/v1/providers/${engine}/presets`, preset);
}

/**
 * 更新 Provider 预设
 */
export async function updateProviderPreset(
  engine: string,
  presetId: string,
  preset: ProviderPresetCreateRequest
): Promise<ProviderPresetResponse> {
  return put<ProviderPresetResponse>(`/v1/providers/${engine}/presets/${presetId}`, preset);
}

/**
 * 删除 Provider 预设
 */
export async function deleteProviderPreset(engine: string, presetId: string): Promise<void> {
  return del<void>(`/v1/providers/${engine}/presets/${presetId}`);
}

/**
 * 切换到指定的 Provider 预设
 */
export async function switchProvider(
  engine: string,
  presetId: string
): Promise<ProviderConfigResponse> {
  return post<ProviderConfigResponse>(`/v1/providers/${engine}/switch?preset_id=${presetId}`);
}

/**
 * 更新指定引擎的 Provider 配置
 */
export async function updateProviderConfig(
  engine: string,
  config: ProviderConfigUpdateRequest
): Promise<ProviderConfigResponse> {
  return put<ProviderConfigResponse>(`/v1/providers/${engine}`, config);
}

/**
 * 启用指定引擎的 Provider
 */
export async function enableProvider(engine: string): Promise<ProviderConfigResponse> {
  return post<ProviderConfigResponse>(`/v1/providers/${engine}/enable`);
}

/**
 * 禁用指定引擎的 Provider
 */
export async function disableProvider(engine: string): Promise<ProviderConfigResponse> {
  return post<ProviderConfigResponse>(`/v1/providers/${engine}/disable`);
}
