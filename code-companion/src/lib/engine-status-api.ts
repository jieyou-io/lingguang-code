/**
 * 引擎状态相关 API
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export interface EngineStatus {
  name: string;
  engine: 'claude' | 'codex' | 'gemini';
  status: 'online' | 'offline' | 'degraded';
  latency: number;
  message?: string;
}

export interface EngineStatusListResponse {
  engines: EngineStatus[];
}

/**
 * 获取所有引擎的状态
 */
export async function getEnginesStatus(): Promise<EngineStatusListResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/engines/status`);

  if (!response.ok) {
    throw new Error(`Failed to fetch engines status: ${response.statusText}`);
  }

  return response.json();
}
