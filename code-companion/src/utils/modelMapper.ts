/**
 * 模型名称映射工具
 * 将后端返回的完整模型名称映射到前端定义的简化模型名称
 */
import type { AIModel, AIEngine } from '@/types';

/**
 * 将后端返回的模型名称映射到前端 AIModel 类型
 */
export function mapBackendModelToFrontend(
  backendModel: string | null | undefined,
  engine?: AIEngine
): AIModel {
  if (!backendModel) {
    // 根据引擎返回默认模型
    if (engine === 'codex') {
      return 'gpt-5';
    } else if (engine === 'gemini') {
      return 'gemini-2.5-pro';
    }
    return 'claude-sonnet-4-5'; // Claude 默认模型
  }

  if (engine === 'codex' || engine === 'gemini') {
    return backendModel as AIModel;
  }

  if (engine === 'claude' && /^[a-z]+[a-z0-9-]*$/.test(backendModel)) {
    return backendModel as AIModel;
  }

  const model = backendModel.toLowerCase();

  if (model.includes('claude-sonnet-4-5-thinking')) {
    return 'claude-sonnet-4-5-thinking';
  }
  // Claude 模型映射
  if (model.includes('claude-sonnet-4-5') || model.includes('claude-sonnet-4-20250')) {
    return 'claude-sonnet-4-5';
  }
  if (model.includes('claude-opus-4-5') || model.includes('claude-opus-4-20250')) {
    return 'claude-opus-4-5';
  }
  if (model.includes('claude-4-sonnet') || model.includes('claude-sonnet-3-7')) {
    return 'claude-4-sonnet';
  }
  if (model.includes('claude-4-opus') || model.includes('claude-opus-3-7')) {
    return 'claude-4-opus';
  }

  // GPT 模型映射
  if (model.includes('gpt-5-mini') || model.includes('gpt-5-turbo')) {
    return 'gpt-5-mini';
  }
  if (model.includes('gpt-5')) {
    return 'gpt-5';
  }

  // Gemini 模型映射
  if (model.includes('gemini-2.5-flash') || model.includes('gemini-flash')) {
    return 'gemini-2.5-flash';
  }
  if (model.includes('gemini-2.5-pro') || model.includes('gemini-pro')) {
    return 'gemini-2.5-pro';
  }
  if (model.includes('gemini-3-flash')) {
    return 'gemini-3-flash';
  }
  if (model.includes('gemini-3-pro')) {
    return 'gemini-3-pro';
  }

  // 未知模型，根据引擎返回默认值
  console.warn(`Unknown model: ${backendModel}, using default for engine: ${engine || 'claude'}`);
  if (engine === 'codex') {
    return 'gpt-5';
  } else if (engine === 'gemini') {
    return 'gemini-2.5-pro';
  }
  return 'claude-sonnet-4-5';
}
