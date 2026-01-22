/**
 * 会话数据管理 Composable
 *
 * 🔥 支持三引擎会话列表合并：Claude + Codex + Gemini
 */
import { ref } from 'vue';
import { get, del } from '@/lib/api';
import type { Session } from '@/types';

/**
 * 后端会话响应类型
 */
interface BackendSession {
  id: string;
  project_id?: string;
  project_path?: string;
  projectPath?: string;  // Codex/Gemini 使用 camelCase
  created_at: number;
  first_message?: string | null;
  model?: string | null;
  engine?: string;
}

interface SessionListResponse {
  sessions: BackendSession[];
}

/**
 * 将后端会话数据转换为前端格式
 */
function transformSession(bs: BackendSession, projectId: string): Session {
  return {
    id: bs.id,
    projectId: bs.project_id || projectId,
    title: bs.first_message || '未命名会话',
    status: 'completed' as const,
    engine: (bs.engine || 'claude') as any,
    model: bs.model as any,
    createdAt: new Date(bs.created_at * 1000),
    updatedAt: new Date(bs.created_at * 1000),
    tokenCount: 0,
    cost: 0,
    contextSize: 0,
    maxContext: 200000,
    messages: [],
  };
}

export function useSessions(projectId: string, projectPath?: string) {
  const sessions = ref<Session[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /**
   * 加载会话数据 - 合并三引擎会话
   */
  async function loadSessions() {
    loading.value = true;
    error.value = null;

    try {
      const response = await get<SessionListResponse>(`/v1/projects/${projectId}/sessions`).catch(() => ({
        sessions: [],
      }));
      const allSessions = response.sessions || [];

      // 转换为前端格式并按更新时间排序
      sessions.value = allSessions
        .map(bs => transformSession(bs, projectId))
        .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());

      console.log('[useSessions] Loaded sessions:', {
        total: sessions.value.length,
      });
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载会话失败';
      console.error('Failed to load sessions:', err);
    } finally {
      loading.value = false;
    }
  }

  /**
   * 删除会话
   */
  async function removeSession(sessionId: string) {
    // 找到要删除的会话，根据引擎类型调用不同的删除接口
    const session = sessions.value.find(s => s.id === sessionId);
    if (!session) {
      throw new Error('Session not found');
    }

    try {
      switch (session.engine) {
        case 'codex':
          await del(`/v1/sessions/codex/${sessionId}`);
          break;
        case 'gemini':
          // Gemini 删除需要 projectPath
          const decodedPath = projectPath || decodeProjectId(projectId);
          await del(`/v1/sessions/gemini/${sessionId}?project_path=${encodeURIComponent(decodedPath)}`);
          break;
        default:
          // Claude
          await del(`/v1/sessions/claude/${projectId}/${sessionId}`);
      }
      sessions.value = sessions.value.filter(s => s.id !== sessionId);
    } catch (err) {
      error.value = err instanceof Error ? err.message : '删除会话失败';
      throw err;
    }
  }

  return {
    sessions,
    loading,
    error,
    loadSessions,
    removeSession,
  };
}

/**
 * 将 projectId 解码为 projectPath
 * 例如: -Users-king-Documents-ai--code -\u003e /Users/king/Documents/ai-code
 */
function decodeProjectId(projectId: string): string {
  if (!projectId) return '';
  // 🔥 编码规则：/ -> -，- -> --
  // 解码规则：先把 -- 转为占位符，再把 - 转为 /，最后把占位符转回 -
  const placeholder = '\x00';
  return projectId
    .replace(/--/g, placeholder)
    .replace(/-/g, '/')
    .replace(new RegExp(placeholder, 'g'), '-');
}
