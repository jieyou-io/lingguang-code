export type AIEngine = 'claude' | 'codex' | 'gemini';

export interface Project {
  id: string;
  name: string;
  path: string;
  lastActive: Date;
  activeSessions: number;
  totalTokens: number;
  totalCost: number;
}

export type AIModel =
  | 'claude-4-sonnet'
  | 'claude-4-opus'
  | 'claude-sonnet-4-5'
  | 'claude-sonnet-4-5-thinking'
  | 'claude-opus-4-5'
  | 'gpt-5'
  | 'gpt-5-mini'
  | 'gemini-2.5-pro'
  | 'gemini-2.5-flash'
  | 'gemini-3-flash'
  | 'gemini-3-pro'
  | (string & {});

export interface SessionSettings {
  engine: AIEngine;
  model: AIModel;
  thinkingEnabled: boolean;
  planModeEnabled: boolean;
}

export interface Session {
  id: string;
  projectId: string;
  title: string;
  status: 'active' | 'paused' | 'completed' | 'error';
  engine: AIEngine;
  model?: AIModel;
  thinkingEnabled?: boolean;
  planModeEnabled?: boolean;
  createdAt: Date;
  updatedAt: Date;
  tokenCount: number;
  cost: number;
  contextSize: number;
  maxContext: number;
  messages: Message[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  tokens?: number;
  isStreaming?: boolean;
  codeBlocks?: CodeBlock[];
  toolUseBlocks?: ToolUseBlock[];
  sessionId?: string;
}

export interface CodeBlock {
  language: string;
  code: string;
  filename?: string;
  diff?: boolean;
}

export interface ToolUseBlock {
  type: 'tool_use';
  id: string;
  name: string;
  input?: any;
}

export interface ContextItem {
  id: string;
  type: 'file' | 'selection' | 'history' | 'plugin' | 'system';
  name: string;
  path?: string;
  tokens: number;
  pinned: boolean;
  addedAt: Date;
  lastAccessed?: Date;
  content?: string;
  priority: number;
}

export interface TokenStats {
  today: number;
  thisWeek: number;
  thisMonth: number;
  byEngine: Record<AIEngine, number>;
  costBreakdown: {
    period: string;
    tokens: number;
    cost: number;
  }[];
}

export type MCPEngine = 'claude-code' | 'codex' | 'gemini-cli';

export interface MCPTool {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  engine: MCPEngine;
  icon: string;
}
