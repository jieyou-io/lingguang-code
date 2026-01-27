import { computed, onBeforeUnmount, ref, unref, type ComputedRef, type Ref } from 'vue';
import type { AIEngine } from '@/types';

export type StreamingStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'streaming'
  | 'interrupted'
  | 'completed'
  | 'error';

export interface ToolUsePayload {
  id: string;
  name: string;
  input?: any;
  meta?: any;
}

type MaybeRef<T> = T | Ref<T> | ComputedRef<T>;

interface UseStreamingOptions {
  sessionId: MaybeRef<string>;
  engine: MaybeRef<AIEngine>;
  protocol?: 'sse' | 'websocket';
  baseUrl?: MaybeRef<string>;
  projectPath?: MaybeRef<string>;
  model?: MaybeRef<string>;
  planMode?: MaybeRef<boolean>;
  maxThinkingTokens?: MaybeRef<number | null>;
  tabId?: MaybeRef<string | null>;
  enabled?: MaybeRef<boolean>;
  onToken?: (token: string, fullContent: string) => void;
  onComplete?: (fullContent: string) => void;
  onError?: (error: Error) => void;
  onToolUse?: (toolUse: ToolUsePayload) => void;
  onPermissionRequest?: (payload: any, sessionId: string) => void;
  onSessionInit?: (sessionId: string) => void;
  onSessionAlias?: (sessionId: string) => void;
}

interface UseStreamingReturn {
  status: Ref<StreamingStatus>;
  isStreaming: ComputedRef<boolean>;
  content: Ref<string>;
  send: (message: string) => Promise<string | null>;
  interrupt: () => Promise<void>;
  resume: () => Promise<void>;
  reset: () => void;
}

const apiBaseUrl =
    import.meta.env.VITE_API_BASE_URL;

export function useStreaming(options: UseStreamingOptions): UseStreamingReturn {
  const status = ref<StreamingStatus>('idle');
  const content = ref('');
  const eventSource = ref<EventSource | null>(null);
  const activeSessionId = ref<string | null>(null);
  const lastPrompt = ref<string | null>(null);
  const lastErrorAt = ref<number | null>(null);

  const isStreaming = computed(
    () => status.value === 'streaming' || status.value === 'connecting'
  );

  const resolveBaseUrl = () => unref(options.baseUrl) || apiBaseUrl;
  const resolveEngine = () => unref(options.engine);
  const resolveSessionId = () => unref(options.sessionId);
  const resolveProjectPath = () => unref(options.projectPath);
  const resolveModel = () => unref(options.model);
  const resolvePlanMode = () => unref(options.planMode);
  const resolveMaxThinkingTokens = () => unref(options.maxThinkingTokens);
  const resolveTabId = () => unref(options.tabId);
  const resolveEnabled = () => unref(options.enabled);

  const setError = (error: Error) => {
    const now = Date.now();
    if (lastErrorAt.value && now - lastErrorAt.value < 1000) {
      return;
    }
    lastErrorAt.value = now;
    status.value = 'error';
    options.onError?.(error);
  };

  const resetContent = () => {
    content.value = '';
  };

  const disconnect = () => {
    eventSource.value?.close();
    eventSource.value = null;
  };

  const extractText = (payload: any): string => {
    if (!payload) return '';
    if (typeof payload === 'string') return payload;

    if (payload.type === 'message' && payload.role === 'user') {
      return '';
    }

    // Codex event payloads (e.g. item.completed with agent_message)
    if (payload.type && payload.item && typeof payload.item === 'object') {
      if (payload.item.type === 'agent_message' && typeof payload.item.text === 'string') {
        return payload.item.text;
      }
    }

    const contentValue =
      payload.message?.content ?? payload.content ?? payload.delta?.content;

    if (typeof contentValue === 'string') return contentValue;

    if (Array.isArray(contentValue)) {
      const parts: string[] = [];
      for (const item of contentValue) {
        if (typeof item === 'string') {
          parts.push(item);
        } else if (item && typeof item === 'object') {
          if (
            (item.type === 'text' || item.type === 'output_text' || item.type === 'input_text') &&
            typeof item.text === 'string'
          ) {
            parts.push(item.text);
          }
        }
      }
      return parts.join('');
    }

    if (typeof payload.text === 'string') return payload.text;

    return '';
  };

  const extractToolUses = (payload: any): ToolUsePayload[] => {
    const contentValue = payload?.message?.content ?? payload?.content;
    if (!Array.isArray(contentValue)) return [];

    return contentValue
      .filter((item: any) => item && item.type === 'tool_use')
      .map((item: any) => ({
        id: item.id || '',
        name: item.name || '',
        input: item.input,
        meta: item.meta ?? payload?.meta,
      }))
      .filter((item: ToolUsePayload) => item.id && item.name);
  };

  const handlePayload = (payload: any) => {
    if (payload?.type === 'init' && typeof payload.session_id === 'string') {
      options.onSessionAlias?.(payload.session_id);
    }

    const text = extractText(payload);
    if (text) {
      const nextContent = content.value + text;
      content.value = nextContent;
      options.onToken?.(text, nextContent);
    }

    const toolUses = extractToolUses(payload);
    toolUses.forEach((toolUse) => options.onToolUse?.(toolUse));
  };

  const connectSse = (sessionId: string) => {
    disconnect();
    status.value = 'connecting';

    const sseUrl = `${resolveBaseUrl()}/v1/${resolveEngine()}/stream?sessionId=${encodeURIComponent(
      sessionId
    )}`;
    eventSource.value = new EventSource(sseUrl);

    eventSource.value.onopen = () => {
      status.value = 'connected';
    };

    const parseJsonSafe = (raw: any) => {
      if (raw == null) return null;
      if (raw === 'undefined') return null;
      if (typeof raw !== 'string') return null;
      const trimmed = raw.trim();
      if (!trimmed || trimmed === 'undefined') return null;
      try {
        return JSON.parse(trimmed);
      } catch {
        return null;
      }
    };

    const handleEvent = (event: MessageEvent) => {
      if (!event?.data) return;
      const data = parseJsonSafe(event.data);
      if (!data?.payload) {
        return;
      }
      status.value = 'streaming';
      handlePayload(data.payload);
    };

    eventSource.value.addEventListener('session_init', (event) => {
      const data = parseJsonSafe((event as MessageEvent).data);
      if (!data) return;
      status.value = 'connected';
      if (data?.sessionId) {
        activeSessionId.value = data.sessionId;
        options.onSessionInit?.(data.sessionId);
      }
    });

    eventSource.value.addEventListener('output', handleEvent);

    eventSource.value.addEventListener('permission_request', (event) => {
      const data = parseJsonSafe((event as MessageEvent).data);
      if (!data) return;
      status.value = 'streaming';
      if (data?.payload) {
        handlePayload(data.payload);
      }
      if (data?.sessionId) {
        options.onPermissionRequest?.(data.payload, data.sessionId);
      }
    });

    eventSource.value.addEventListener('error', (event) => {
      const data = parseJsonSafe((event as MessageEvent).data);
      const message = data?.payload?.error || 'SSE error';
      if (typeof message === 'string' && message.startsWith('Error executing tool')) {
        const nextContent = `${content.value}\n\n[工具错误] ${message}`;
        content.value = nextContent;
        options.onToken?.('', nextContent);
        return;
      }
      setError(new Error(message));
      disconnect();
    });

    eventSource.value.addEventListener('complete', (event) => {
      parseJsonSafe((event as MessageEvent).data);
      status.value = 'completed';
      options.onComplete?.(content.value);
      disconnect();
    });

    eventSource.value.onerror = () => {
      if (status.value === 'completed' || status.value === 'error') {
        return;
      }
      setError(new Error('SSE connection error'));
      disconnect();
    };
  };

  const postJson = async (url: string, body: Record<string, any>) => {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      try {
        const data = await response.json();
        errorMessage = data?.detail || data?.error?.message || errorMessage;
      } catch {
        // Ignore JSON parse errors.
      }
      throw new Error(errorMessage);
    }

    return response.json();
  };

  const executeSession = async (message: string) => {
    const projectPath = resolveProjectPath();
    if (!projectPath) {
      throw new Error('Missing project path');
    }

    const payload: Record<string, any> = {
      projectPath,
      prompt: message,
    };

    const model = resolveModel();
    if (model) payload.model = model;
    const planMode = resolvePlanMode();
    if (planMode !== undefined) payload.planMode = planMode;
    const maxThinkingTokens = resolveMaxThinkingTokens();
    if (maxThinkingTokens !== undefined) {
      payload.maxThinkingTokens = maxThinkingTokens;
    }
    const tabId = resolveTabId();
    if (tabId) payload.tabId = tabId;

    if (resolveEngine() === 'codex') {
      payload.mode = 'read-only';
      payload.json = true;
    }

    const response = await postJson(
      `${resolveBaseUrl()}/v1/${resolveEngine()}/execute`,
      payload
    );

    return response?.sessionId as string;
  };

  const resumeSession = async (sessionId: string, message: string) => {
    const projectPath = resolveProjectPath();
    if (!projectPath) {
      throw new Error('Missing project path');
    }

    const payload: Record<string, any> = {
      sessionId,
      projectPath,
      prompt: message,
    };

    const model = resolveModel();
    if (model) payload.model = model;
    const planMode = resolvePlanMode();
    if (planMode !== undefined) payload.planMode = planMode;
    const maxThinkingTokens = resolveMaxThinkingTokens();
    if (maxThinkingTokens !== undefined) {
      payload.maxThinkingTokens = maxThinkingTokens;
    }
    const tabId = resolveTabId();
    if (tabId) payload.tabId = tabId;

    if (resolveEngine() === 'codex') {
      payload.mode = 'read-only';
      payload.json = true;
    }

    const resumeEndpoint = resolveEngine() === 'gemini' ? 'continue' : 'resume';
    const response = await postJson(
      `${resolveBaseUrl()}/v1/${resolveEngine()}/${resumeEndpoint}`,
      payload
    );

    return response?.sessionId as string;
  };

  const send = async (message: string) => {
    if (resolveEnabled() === false) {
      return null;
    }

    resetContent();
    lastPrompt.value = message;

    try {
    const currentSessionId = resolveSessionId();
    const isTempSession = /^\d{13,}$/.test(currentSessionId);
    const sessionId = isTempSession
      ? await executeSession(message)
      : await resumeSession(currentSessionId, message);
    activeSessionId.value = sessionId;
    connectSse(sessionId);
      return sessionId;
    } catch (error) {
      setError(error as Error);
      return null;
    }
  };

  const interrupt = async () => {
    status.value = 'interrupted';
    disconnect();

    const sessionId = activeSessionId.value;
    if (!sessionId) return;

    try {
      await postJson(`${resolveBaseUrl()}/v1/${resolveEngine()}/cancel`, {
        sessionId,
      });
    } catch (error) {
      setError(error as Error);
    }
  };

  const resume = async () => {
    if (!lastPrompt.value) {
      return;
    }

    try {
      const sessionId = activeSessionId.value || resolveSessionId();
      if (!sessionId) {
        return;
      }
      const isTempSession = /^\d{13,}$/.test(sessionId);
      const resumedSessionId = isTempSession
        ? await executeSession(lastPrompt.value)
        : await resumeSession(sessionId, lastPrompt.value);
      activeSessionId.value = resumedSessionId;
      connectSse(resumedSessionId);
    } catch (error) {
      setError(error as Error);
    }
  };

  const reset = () => {
    disconnect();
    resetContent();
    status.value = 'idle';
    activeSessionId.value = null;
  };

  onBeforeUnmount(() => {
    disconnect();
  });

  return {
    status,
    isStreaming,
    content,
    send,
    interrupt,
    resume,
    reset,
  };
}
