/**
 * 设置页面 API 客户端
 *
 * 提供 Plugins、Agents、Skills 的完整 CRUD 操作
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

// ============= 类型定义 =============

export interface Plugin {
  id: string;
  path: string;
  enabled: boolean;
}

export interface PluginListResponse {
  plugins: Plugin[];
}

export interface PluginInstallRequest {
  plugin_ref: string;
}

export interface PluginInstallResponse {
  id: string;
  installed: boolean;
}

export interface Agent {
  id: string;
  path: string;
  metadata: {
    enabled?: boolean;
    name?: string;
    tools?: string[];
    [key: string]: any;
  };
  content: string;
  enabled: boolean;
}

export interface AgentListResponse {
  agents: Agent[];
}

export interface AgentCreateRequest {
  id: string;
  metadata: {
    enabled?: boolean;
    name?: string;
    tools?: string[];
    [key: string]: any;
  };
  content: string;
}

export interface AgentUpdateRequest {
  metadata: {
    enabled?: boolean;
    name?: string;
    tools?: string[];
    [key: string]: any;
  };
  content: string;
}

export interface Skill {
  id: string;
  path: string;
  metadata: {
    enabled?: boolean;
    description?: string;
    [key: string]: any;
  };
  content: string;
  enabled: boolean;
}

export interface SkillListResponse {
  skills: Skill[];
}

export interface SkillCreateRequest {
  id: string;
  metadata: {
    enabled?: boolean;
    description?: string;
    [key: string]: any;
  };
  content: string;
}

export interface SkillUpdateRequest {
  metadata: {
    enabled?: boolean;
    description?: string;
    [key: string]: any;
  };
  content: string;
}

// ============= Plugins API =============

/**
 * 列出所有插件
 */
export async function listPlugins(): Promise<PluginListResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/claude/plugins`);
  if (!response.ok) {
    throw new Error(`Failed to list plugins: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 安装新插件
 */
export async function installPlugin(pluginRef: string): Promise<PluginInstallResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/claude/plugins`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plugin_ref: pluginRef })
  });
  if (!response.ok) {
    throw new Error(`Failed to install plugin: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 启用插件
 */
export async function enablePlugin(pluginId: string): Promise<Plugin> {
  const response = await fetch(
    `${API_BASE_URL}/v1/claude/plugins/${encodeURIComponent(pluginId)}/enable`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Failed to enable plugin: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 禁用插件
 */
export async function disablePlugin(pluginId: string): Promise<Plugin> {
  const response = await fetch(
    `${API_BASE_URL}/v1/claude/plugins/${encodeURIComponent(pluginId)}/disable`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Failed to disable plugin: HTTP ${response.status}`);
  }
  return response.json();
}

// ============= Agents API =============

/**
 * 列出所有代理
 */
export async function listAgents(): Promise<AgentListResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/claude/agents`);
  if (!response.ok) {
    throw new Error(`Failed to list agents: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 获取单个代理详情
 */
export async function getAgent(agentId: string): Promise<Agent> {
  const response = await fetch(
    `${API_BASE_URL}/v1/claude/agents/${encodeURIComponent(agentId)}`
  );
  if (!response.ok) {
    throw new Error(`Failed to get agent: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 创建新代理
 */
export async function createAgent(request: AgentCreateRequest): Promise<Agent> {
  const response = await fetch(`${API_BASE_URL}/v1/claude/agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    throw new Error(`Failed to create agent: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 更新代理
 */
export async function updateAgent(
  agentId: string,
  request: AgentUpdateRequest
): Promise<Agent> {
  const response = await fetch(
    `${API_BASE_URL}/v1/claude/agents/${encodeURIComponent(agentId)}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to update agent: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 删除代理
 */
export async function deleteAgent(agentId: string): Promise<{ success: boolean }> {
  const response = await fetch(
    `${API_BASE_URL}/v1/claude/agents/${encodeURIComponent(agentId)}`,
    { method: 'DELETE' }
  );
  if (!response.ok) {
    throw new Error(`Failed to delete agent: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 启用代理
 */
export async function enableAgent(agentId: string): Promise<Agent> {
  const response = await fetch(
    `${API_BASE_URL}/v1/claude/agents/${encodeURIComponent(agentId)}/enable`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Failed to enable agent: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 禁用代理
 */
export async function disableAgent(agentId: string): Promise<Agent> {
  const response = await fetch(
    `${API_BASE_URL}/v1/claude/agents/${encodeURIComponent(agentId)}/disable`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Failed to disable agent: HTTP ${response.status}`);
  }
  return response.json();
}

// ============= Skills API =============

/**
 * 列出所有技能
 */
export async function listSkills(): Promise<SkillListResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/claude/skills`);
  if (!response.ok) {
    throw new Error(`Failed to list skills: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 获取单个技能详情
 */
export async function getSkill(skillId: string): Promise<Skill> {
  const response = await fetch(
    `${API_BASE_URL}/v1/claude/skills/${encodeURIComponent(skillId)}`
  );
  if (!response.ok) {
    throw new Error(`Failed to get skill: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 创建新技能
 */
export async function createSkill(request: SkillCreateRequest): Promise<Skill> {
  const response = await fetch(`${API_BASE_URL}/v1/claude/skills`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    throw new Error(`Failed to create skill: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 更新技能
 */
export async function updateSkill(
  skillId: string,
  request: SkillUpdateRequest
): Promise<Skill> {
  const response = await fetch(
    `${API_BASE_URL}/v1/claude/skills/${encodeURIComponent(skillId)}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to update skill: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 删除技能
 */
export async function deleteSkill(skillId: string): Promise<{ success: boolean }> {
  const response = await fetch(
    `${API_BASE_URL}/v1/claude/skills/${encodeURIComponent(skillId)}`,
    { method: 'DELETE' }
  );
  if (!response.ok) {
    throw new Error(`Failed to delete skill: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 启用技能
 */
export async function enableSkill(skillId: string): Promise<Skill> {
  const response = await fetch(
    `${API_BASE_URL}/v1/claude/skills/${encodeURIComponent(skillId)}/enable`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Failed to enable skill: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * 禁用技能
 */
export async function disableSkill(skillId: string): Promise<Skill> {
  const response = await fetch(
    `${API_BASE_URL}/v1/claude/skills/${encodeURIComponent(skillId)}/disable`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Failed to disable skill: HTTP ${response.status}`);
  }
  return response.json();
}
