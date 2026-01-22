/**
 * 聊天会话数据管理 Composable
 *
 * 🔥 支持三引擎会话历史加载：Claude / Codex / Gemini
 */
import { ref } from 'vue';
import {
  getClaudeSessionHistory,
  getCodexSessionHistory,
  getGeminiSessionHistory,
} from '@/lib/services/sessions';
import { get } from '@/lib/api';
import type { Message, Session, AIEngine } from '@/types';
import { mapBackendModelToFrontend } from '@/utils/modelMapper';

interface SessionListResponse {
  sessions: Array<{
    id: string;
    engine?: string;
    model?: string;
    created_at?: number;
    last_message_timestamp?: string;
  }>;
}

export function useChatSession(sessionId: string, projectId: string, engineFromUrl?: string) {
  const messages = ref<Message[]>([]);
  const session = ref<Session | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const hasMore = ref(false);
  const projectPath = ref<string | undefined>(undefined); // 🔥 保存项目路径（Gemini 历史返回）
  const currentPage = ref(0);
  const pageSize = 50; // 每页加载50条消息

  /**
   * 加载会话历史（支持分页）
   */
  async function loadSessionHistory(loadMore = false) {
    loading.value = true;
    error.value = null;

    try {
      // 🔥 优先使用 URL 传递的引擎类型
      let sessionMeta: any = null;
      let engine: AIEngine = (engineFromUrl as AIEngine) || 'claude';

      // 如果 URL 没有传递引擎类型，尝试从项目会话列表中查找
      if (!engineFromUrl) {
        try {
          const response = await get<SessionListResponse>(
            `/v1/projects/${projectId}/sessions`
          ).catch(() => ({ sessions: [] }));

          sessionMeta = response.sessions.find((s: any) => s.id === sessionId);
          if (sessionMeta) {
            engine = (sessionMeta.engine as AIEngine) || engine;
          }

          console.log('[useChatSession] Engine detected:', engine, 'sessionMeta:', sessionMeta);
        } catch (err) {
          console.warn('[useChatSession] Failed to fetch session meta:', err);
        }
      } else {
        console.log('[useChatSession] Using engine from URL:', engineFromUrl);
      }

      // 🔥 根据引擎类型调用不同的历史 API
      let response: any;
      switch (engine) {
        case 'codex':
          response = await getCodexSessionHistory(sessionId);
          break;
        case 'gemini':
          response = await getGeminiSessionHistory(sessionId);
          // 🔥 提取并保存项目路径
          if (response.project_path) {
            projectPath.value = response.project_path;
            console.log('[useChatSession] Extracted project_path:', response.project_path);
          }
          break;
        default:
          response = await getClaudeSessionHistory(projectId, sessionId);
      }

      console.log('[useChatSession] Loading history for engine:', engine, 'sessionId:', sessionId);

      // 🔥 根据引擎类型转换消息格式
      let normalizedMessages: any[] = [];

      if (engine === 'codex') {
        // Codex 格式：{ type, payload: { role, content: [{ type, text }] } }
        normalizedMessages = (response.messages || [])
          .filter((msg: any) => {
            // 只保留 response_item 类型且有 role 的消息
            if (msg.type !== 'response_item') return false;
            const payload = msg.payload || {};
            if (!payload.role) return false;
            if (payload.role !== 'user' && payload.role !== 'assistant') return false;
            return true;
          })
          .map((msg: any) => {
            const payload = msg.payload || {};
            const content = extractCodexContent(payload.content);
            return {
              message: { role: payload.role, content },
              messageId: payload.id || msg.timestamp,
              sentAt: msg.timestamp,
              receivedAt: msg.timestamp,
            };
          });
      } else {
        // Claude/Gemini 格式：{ message: { role, content } }
        normalizedMessages = response.messages || [];
      }

      // 转换后端消息格式为前端格式
      const allMessages = normalizedMessages
        .filter((msg: any) => {
          // 只保留有 message.role 的消息
          if (!msg.message || !msg.message.role) return false;

          // 只保留 user 和 assistant 消息
          if (msg.message.role !== 'user' && msg.message.role !== 'assistant') return false;

          return true;
        })
        .map((msg: any, index: number) => {
          const content = extractContent(msg.message.content);
          return {
            id: msg.messageId || `msg-${index}`,
            role: msg.message.role,
            content,
            timestamp: new Date(msg.receivedAt || msg.sentAt || Date.now()),
            tokens: 0,
          };
        })
        .map((msg: Message) => {
          // 移除 <thinking> 标签及其内容
          let content = msg.content.replace(/<thinking>[\s\S]*?<\/thinking>/g, '').trim();
          // 移除其他系统标签
          content = content.replace(/<command-message>[\s\S]*?<\/command-message>/g, '').trim();
          content = content.replace(/<command-name>[\s\S]*?<\/command-name>/g, '').trim();
          content = content.replace(/<command-args>[\s\S]*?<\/command-args>/g, '').trim();
          content = content.replace(/<local-command-stdout>[\s\S]*?<\/local-command-stdout>/g, '').trim();
          // 🔥 移除 Codex 系统消息
          content = content.replace(/<environment_context>[\s\S]*?<\/environment_context>/g, '').trim();
          content = content.replace(/<permissions instructions>[\s\S]*?<\/permissions instructions>/g, '').trim();
          return { ...msg, content };
        })
        .filter((msg: Message) => {
          // 过滤掉空消息或只有空白字符的消息
          const trimmed = msg.content.trim();
          if (!trimmed) return false;

          // 过滤掉系统生成的消息
          if (trimmed.includes('Caveat: The messages below were generated by the user while running local commands')) return false;
          if (trimmed === 'Warmup') return false;
          // 🔥 过滤 Codex 系统消息
          if (trimmed.startsWith('# AGENTS.md instructions')) return false;

          return true;
        });

      // 分页处理：只加载最新的消息
      const totalMessages = allMessages.length;
      const startIndex = loadMore ? currentPage.value * pageSize : Math.max(0, totalMessages - pageSize);
      const endIndex = loadMore ? (currentPage.value + 1) * pageSize : totalMessages;

      const pagedMessages = allMessages.slice(startIndex, endIndex);

      // 更新分页状态
      if (loadMore) {
        messages.value = [...pagedMessages, ...messages.value];
        currentPage.value += 1;
      } else {
        messages.value = pagedMessages;
        currentPage.value = 1;
      }

      // 检查是否还有更多消息
      hasMore.value = startIndex > 0;

      // 创建会话对象
      // 使用第一条用户消息作为标题（截取前50个字符）
      const firstUserMessage = allMessages.find((m: Message) => m.role === 'user');
      let title = sessionId;
      if (firstUserMessage && firstUserMessage.content.trim()) {
        // 清理后的内容作为标题
        const cleanContent = firstUserMessage.content.trim();
        title = cleanContent.length > 50
          ? cleanContent.substring(0, 50) + '...'
          : cleanContent;
      }

      session.value = {
        id: sessionId,
        projectId: projectId,
        title,
        status: 'completed',
        engine: engine,
        model: mapBackendModelToFrontend(sessionMeta?.model, engine),
        createdAt: new Date(sessionMeta?.created_at ? sessionMeta.created_at * 1000 : Date.now()),
        updatedAt: new Date(sessionMeta?.last_message_timestamp || Date.now()),
        tokenCount: 0,
        cost: 0,
        contextSize: 0,
        maxContext: 200000,
        messages: messages.value,
      };
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载会话失败';
      console.error('Failed to load session history:', err);
    } finally {
      loading.value = false;
    }
  }

  /**
   * 提取消息内容
   * 支持字符串和数组格式的内容
   */
  function extractContent(content: any): string {
    // 字符串格式直接返回
    if (typeof content === 'string') {
      return content;
    }

    // 数组格式：提取所有 text 类型的内容
    if (Array.isArray(content)) {
      const textParts: string[] = [];

      for (const item of content) {
        if (typeof item === 'string') {
          textParts.push(item);
        } else if (item && typeof item === 'object') {
          // 提取 text 类型的内容
          if (item.type === 'text' && item.text) {
            textParts.push(item.text);
          }
          // tool_use 和 thinking 类型不显示在主消息中
        }
      }

      return textParts.join('\n\n');
    }

    return '';
  }

  /**
   * 🔥 提取 Codex 消息内容
   * Codex 格式：content: [{ type: "input_text" | "output_text", text: "..." }]
   */
  function extractCodexContent(content: any): string {
    if (typeof content === 'string') {
      return content;
    }

    if (Array.isArray(content)) {
      const textParts: string[] = [];

      for (const item of content) {
        if (typeof item === 'string') {
          textParts.push(item);
        } else if (item && typeof item === 'object') {
          // Codex 使用 input_text 和 output_text 类型
          if ((item.type === 'input_text' || item.type === 'output_text') && item.text) {
            textParts.push(item.text);
          }
        }
      }

      return textParts.join('\n\n');
    }

    return '';
  }

  return {
    messages,
    session,
    loading,
    error,
    hasMore,
    loadSessionHistory,
    projectPath, // 🔥 返回项目路径
  };
}
