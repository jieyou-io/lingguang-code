<template>
  <AppShell hide-nav>
    <div v-if="!initialized" class="flex items-center justify-center h-screen">
      <div class="animate-pulse text-muted-foreground">加载中...</div>
    </div>
    <div v-else-if="!hasProject" class="flex items-center justify-center h-screen">
      <div class="text-center">
        <p class="text-muted-foreground mb-4">请先选择一个项目</p>
        <button
          class="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          @click="router.push('/projects')"
        >
          选择项目
        </button>
      </div>
    </div>
    <div v-else class="flex flex-col h-screen">
      <Header :title="session.title || sessionId" back>
        <template #actions>
          <div class="flex items-center gap-1">
            <StreamingIndicator :status="status" class-name="mr-2" />

            <button
              v-if="status === 'interrupted'"
              class="p-2 rounded-lg hover:bg-secondary transition-colors"
              @click="handleResume"
            >
              <Play class="w-4 h-4 text-primary" />
            </button>
            <button
              v-else-if="isStreaming"
              class="p-2 rounded-lg hover:bg-secondary transition-colors"
              @click="handleStop"
            >
              <Pause class="w-4 h-4 text-warning" />
            </button>

            <button
              class="p-2 rounded-lg hover:bg-secondary transition-colors disabled:opacity-50"
              :disabled="isStreaming"
              @click="handleRetry"
            >
              <RotateCcw class="w-4 h-4 text-muted-foreground" />
            </button>
            <button
              class="p-2 rounded-lg hover:bg-secondary transition-colors"
              title="查看代码文件"
              @click="handleViewCode"
            >
              <FileCode class="w-4 h-4 text-muted-foreground" />
            </button>
            <button class="p-2 rounded-lg hover:bg-secondary transition-colors">
              <MoreVertical class="w-4 h-4 text-muted-foreground" />
            </button>
          </div>
        </template>
      </Header>

      <OfflineIndicator
        :online="online"
        :checkpoint="checkpoint"
        :on-resume="handleResume"
      />

      <ContextBar
        :session="session"
        :context-items="activeContextItems"
        :model="currentModel"
        :thinking-enabled="session.thinkingEnabled"
        :plan-mode-enabled="session.planModeEnabled"
        :on-engine-change="handleEngineChange"
        :on-toggle-pin="handleTogglePin"
        :on-remove-item="handleRemoveContextItem"
        :on-clear-unpinned="handleClearUnpinned"
        :on-add-file="handleAddFile"
        :on-remove-file="handleRemoveFile"
        :on-compress="handleCompress"
        :disabled="isStreaming"
      />

      <div
        ref="messagesContainerRef"
        @scroll="handleScroll"
        class="flex-1 overflow-y-auto px-4 py-4 space-y-4 pb-32"
      >
        <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-full text-muted-foreground">
          <p class="text-lg">开始新对话</p>
          <p class="text-sm">输入消息开始与 AI 交互</p>
        </div>
        <template v-else>
          <div v-if="hasMore && loadingHistory" class="flex justify-center py-2">
            <div class="text-sm text-muted-foreground">加载中...</div>
          </div>
          <MessageBubble v-for="message in messages" :key="message.id" :message="message" />
        </template>
        <div ref="messagesEndRef" />
      </div>

      <ChatInput
        :on-send="handleSend"
        :is-streaming="isStreaming"
        :on-stop="handleStop"
        :disabled="status === 'error' || !online"
        :engine="session.engine"
        :model="currentModel"
        :project-path="currentProjectPath"
        :thinking-enabled="session.thinkingEnabled ?? true"
        :plan-mode-enabled="session.planModeEnabled ?? false"
        :on-engine-change="handleEngineChange"
        :on-model-change="handleModelChange"
        :on-thinking-change="handleThinkingChange"
        :on-plan-mode-change="handlePlanModeChange"
      />

      <CodeFileBrowserDialog
        :open="codeDialogOpen"
        :project-name="session.title"
        @update:open="codeDialogOpen = $event"
      />

      <AskUserQuestionDialog
        :show="showQuestionDialog"
        :questions="pendingQuestion?.questions || []"
        @submit="handleQuestionSubmit"
        @close="closeQuestionDialog"
      />
    </div>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { MoreVertical, Pause, Play, RotateCcw, FileCode } from 'lucide-vue-next';
import AppShell from '@/components/layout/AppShell.vue';
import Header from '@/components/layout/Header.vue';
import ContextBar from '@/components/chat/ContextBar.vue';
import MessageBubble from '@/components/chat/MessageBubble.vue';
import ChatInput from '@/components/chat/ChatInput.vue';
import StreamingIndicator from '@/components/chat/StreamingIndicator.vue';
import OfflineIndicator from '@/components/chat/OfflineIndicator.vue';
import CodeFileBrowserDialog from '@/components/project/CodeFileBrowserDialog.vue';
import AskUserQuestionDialog from '@/components/dialogs/AskUserQuestionDialog.vue';
import { Message, Session, AIEngine, AIModel, ContextItem, ToolUseBlock } from '@/types';
import { useStreaming } from '@/composables/useStreaming';
import { useSessionPersistence } from '@/composables/useSessionPersistence';
import { useChatSession } from '@/composables/useChatSession';
import { useUserQuestion } from '@/composables/useUserQuestion';
import { compressContext } from '@/lib/contextCompression';
import type { CompressionStrategy, CompressionOptions } from '@/components/chat/ContextCompressionDialog.vue';
import { useToast } from '@/composables/useToast';
import { saveSession } from '@/lib/sessionStorage';
import { mapBackendModelToFrontend } from '@/utils/modelMapper';

const route = useRoute();
const router = useRouter();
const sessionId = computed(() => (route.params.sessionId as string) || '1');
const projectId = computed(() => route.params.projectId as string | undefined);
const hasProject = computed(() => Boolean(projectId.value));
// 🔥 从 projectId 解码出实际的项目路径
// 编码规则：/ -> -，- -> --
// 解码规则：先把 -- 转为占位符，再把 - 转为 /，最后把占位符转回 -
const currentProjectPath = computed(() => {
  if (!projectId.value) return '';
  const placeholder = '\x00'; // 使用不可见字符作为占位符
  return projectId.value
    .replace(/--/g, placeholder)  // 先把 -- 转为占位符
    .replace(/-/g, '/')           // 把 - 转为 /
    .replace(new RegExp(placeholder, 'g'), '-'); // 把占位符转回 -
});
// 🔥 修复：从 URL query 获取引擎类型（用于新建会话）
const engineFromQuery = computed(() => (route.query.engine as string) || '');
const { toast } = useToast();

const messagesEndRef = ref<HTMLDivElement | null>(null);
const messagesContainerRef = ref<HTMLDivElement | null>(null);
const streamingMessageIdRef = ref<string | null>(null);
const streamingContentRef = ref('');
const codeDialogOpen = ref(false);
const isLoadingMore = ref(false); // 标记是否正在加载更多历史消息
const isInitialLoad = ref(true); // 标记是否是初始加载
const geminiSessionAlias = ref<string>('');

// AskUserQuestion 功能
const {
  pendingQuestion,
  showQuestionDialog,
  submitAnswers,
  closeQuestionDialog,
  setSendMessageCallback,
  triggerQuestionDialog,
} = useUserQuestion();

// 设置发送消息的回调
onMounted(() => {
  setSendMessageCallback((message: string) => {
    handleSend(message);
  });
});

// 🔥 检测是否是新会话（sessionId 是纯数字时间戳）
const isNewSession = computed(() => /^\d{13,}$/.test(sessionId.value));

const defaultSession = computed<Session>(() => ({
  id: sessionId.value,
  projectId: projectId.value || '',
  title: '新会话',
  status: 'active',
  engine: (engineFromQuery.value || 'claude') as AIEngine,
  createdAt: new Date(),
  updatedAt: new Date(),
  tokenCount: 0,
  cost: 0,
  contextSize: 0,
  maxContext: 100000,
  messages: [],
}));

const {
  session: persistedSession,
  messages,
  contextItems,
  online,
  checkpoint,
  initialized,
  updateSession,
  addMessage,
  updateLastMessage,
  createCheckpoint,
  clearCheckpoint,
  addContextItem,
  removeContextItem,
  togglePinContextItem,
  clearUnpinnedItems,
  setAllContextItems,
} = useSessionPersistence({
  sessionId: sessionId.value,
  onResumeAvailable: () => {
    toast({
      title: '发现未完成的回复',
      description: '点击继续按钮恢复',
    });
  },
});

const session = computed(() => persistedSession.value || defaultSession.value);

// 加载会话历史
const {
  messages: apiMessages,
  session: apiSession,
  loading: loadingHistory,
  hasMore,
  loadSessionHistory
} = useChatSession(
  sessionId.value,
  projectId.value || '',
  engineFromQuery.value  // 🔥 传递 URL 中的引擎类型
);

// 在组件挂载时加载历史消息
onMounted(async () => {
  if (sessionId.value && projectId.value) {
    // 🔥 新会话跳过历史加载（避免 404）
    if (isNewSession.value) {
      console.log('[ChatPage] New session detected, skipping history load');
      isInitialLoad.value = false;
      return;
    }

    // 清空本地缓存的消息，强制从后端重新加载
    messages.value = [];

    await loadSessionHistory();

    // 将从后端加载的消息添加到消息列表
    if (apiMessages.value.length > 0) {
      apiMessages.value.forEach(msg => addMessage(msg));
    }

    // 使用 API 返回的会话数据更新 session
    if (apiSession.value) {
      // 如果 persistedSession 为 null，先用 defaultSession 初始化
      if (!persistedSession.value) {
        saveSession(defaultSession.value);
      }

      // 然后更新引擎、模型和标题
      updateSession({
        engine: apiSession.value.engine,
        model: apiSession.value.model,
        title: apiSession.value.title,
      });
    }

    // 加载完成后滚动到底部
    await nextTick();
    // 添加小延迟确保 DOM 完全渲染
    setTimeout(() => {
      const container = messagesContainerRef.value;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
      // 初始加载完成，允许 watch 触发滚动
      isInitialLoad.value = false;
    }, 100);
  }
});

const activeContextItems = computed(() => contextItems.value);

watch(
  [initialized, persistedSession],
  ([isInitialized, currentSession]) => {
    if (isInitialized && !currentSession) {
      saveSession(defaultSession.value);
    }
  },
  { immediate: true }
);

// 当前活跃的后端 sessionId（由 SSE 返回）
const activeSessionId = ref<string>('');

// 🔥 修复：创建响应式的模型计算属性,确保使用最新选择的模型
const currentModel = computed(() =>
  mapBackendModelToFrontend(session.value.model, session.value.engine)
);

const { status, isStreaming, content: streamingContent, send, interrupt, resume, reset } = useStreaming({
  sessionId: computed(() => session.value.id),
  engine: computed(() => session.value.engine),
  protocol: 'sse',
  projectPath: currentProjectPath, // 🔥 使用从 URL 解码的项目路径
  model: currentModel,
  enabled: hasProject,
  onToken: (token: string, fullContent: string) => {
    streamingContentRef.value = fullContent;
    if (streamingMessageIdRef.value) {
      updateLastMessage(fullContent, true);
    }
  },
  onComplete: (fullContent: string) => {
    if (streamingMessageIdRef.value) {
      updateLastMessage(fullContent, false);
      streamingMessageIdRef.value = null;
      streamingContentRef.value = '';
      clearCheckpoint();

      updateSession({
        tokenCount: (session.value.tokenCount || 0) + Math.floor(fullContent.length * 0.75),
        status: 'active',
      });
    }
  },
  onError: (error: Error) => {
    toast({
      title: '连接错误',
      description: error.message,
      variant: 'destructive',
    });

    if (streamingMessageIdRef.value && streamingContentRef.value) {
      createCheckpoint(streamingContentRef.value, streamingContentRef.value.length);
    }

    if (streamingMessageIdRef.value) {
      updateLastMessage(`${streamingContentRef.value}\n\n[连接中断]`, false);
      streamingMessageIdRef.value = null;
    }
  },
  onSessionInit: (sessionId) => {
    activeSessionId.value = sessionId;
  },
  onSessionAlias: (sessionId) => {
    if (session.value.engine !== 'gemini') {
      return;
    }
    if (!sessionId || sessionId === session.value.id || sessionId === geminiSessionAlias.value) {
      return;
    }
    geminiSessionAlias.value = sessionId;
    updateSession({ id: sessionId });

    const query = { ...route.query };
    if (projectId.value) {
      router.replace({ path: `/chat/${projectId.value}/${sessionId}`, query });
    } else {
      router.replace({ path: `/chat/${sessionId}`, query });
    }
  },
  // 🔥 处理工具调用（权限请求、AskUserQuestion）
  onToolUse: (toolUse) => {
    console.log('[ChatPage] Tool use detected:', toolUse.name, toolUse.id);

    // 将工具调用块添加到当前消息
    if (streamingMessageIdRef.value) {
      const currentMessage = messages.value.find(m => m.id === streamingMessageIdRef.value);
      if (currentMessage) {
        const block: ToolUseBlock = {
          type: 'tool_use',
          id: toolUse.id,
          name: toolUse.name,
          input: toolUse.input,
          meta: toolUse.meta,
        };

        if (!currentMessage.toolUseBlocks) {
          currentMessage.toolUseBlocks = [];
        }
        currentMessage.toolUseBlocks.push(block);
        currentMessage.sessionId = activeSessionId.value;
      }
    }

    if (toolUse.name === 'AskUserQuestion' && toolUse.input?.questions) {
      triggerQuestionDialog(toolUse.input.questions);
    }
  },
  onPermissionRequest: (payload, sessionId) => {
    console.log('[ChatPage] Permission request:', sessionId);
    activeSessionId.value = sessionId;
  },
});

watch([streamingContent, isStreaming], async () => {
  if (isStreaming.value || streamingContent.value) {
    await nextTick();
    messagesEndRef.value?.scrollIntoView({ behavior: 'smooth' });
  }
});

watch(
  () => messages.value.length,
  async () => {
    // 只在非加载更多历史消息且非初始加载时才滚动到底部
    if (messages.value.length > 0 && !isLoadingMore.value && !isInitialLoad.value) {
      await nextTick();
      messagesEndRef.value?.scrollIntoView({ behavior: 'smooth' });
    }
  }
);

const handleEngineChange = (newEngine: AIEngine) => {
  updateSession({ engine: newEngine });
  toast({
    title: '引擎已切换',
    description: `当前使用 ${newEngine.charAt(0).toUpperCase() + newEngine.slice(1)}`,
  });
};

const handleModelChange = (newModel: AIModel) => {
  updateSession({ model: newModel });
  toast({
    title: '模型已切换',
    description: `当前使用 ${newModel}`,
  });
};

const handleThinkingChange = (enabled: boolean) => {
  updateSession({ thinkingEnabled: enabled });
  toast({
    title: enabled ? '思考模式已开启' : '思考模式已关闭',
  });
};

const handlePlanModeChange = (enabled: boolean) => {
  updateSession({ planModeEnabled: enabled });
  toast({
    title: enabled ? 'Plan Mode 已开启' : 'Plan Mode 已关闭',
  });
};

const handleSend = async (content: string) => {
  if (!hasProject.value) {
    toast({
      title: '请先选择项目',
      description: '选择项目后才能开始会话',
      variant: 'destructive',
    });
    return;
  }

  const userMessage: Message = {
    id: Date.now().toString(),
    role: 'user',
    content,
    timestamp: new Date(),
    tokens: Math.floor(content.length * 1.3),
  };

  addMessage(userMessage);

  const aiMessageId = (Date.now() + 1).toString();
  const aiMessage: Message = {
    id: aiMessageId,
    role: 'assistant',
    content: '',
    timestamp: new Date(),
    isStreaming: true,
  };

  streamingMessageIdRef.value = aiMessageId;
  streamingContentRef.value = '';
  addMessage(aiMessage);

  await send(content);
};

const handleStop = () => {
  interrupt();

  if (streamingMessageIdRef.value && streamingContentRef.value) {
    createCheckpoint(streamingContentRef.value, streamingContentRef.value.length);
    updateLastMessage(`${streamingContentRef.value}\n\n[已中断]`, false);
    streamingMessageIdRef.value = null;

    toast({
      title: '已保存进度',
      description: '可以稍后继续',
    });
  }
};

const handleResume = () => {
  if (checkpoint.value) {
    streamingContentRef.value = checkpoint.value.streamingContent;
    const interruptedMessage = messages.value.find(m => m.id === checkpoint.value?.lastMessageId);
    if (interruptedMessage) {
      streamingMessageIdRef.value = checkpoint.value.lastMessageId;
      updateLastMessage(checkpoint.value.streamingContent, true);
    }
  }

  resume();
  toast({
    title: '恢复连接',
    description: '继续接收响应',
  });
};

const handleRetry = () => {
  if (messages.value.length > 0) {
    const lastUserMessage = [...messages.value].reverse().find(m => m.role === 'user');
    if (lastUserMessage) {
      reset();
      clearCheckpoint();
      handleSend(lastUserMessage.content);
    }
  }
};

const handleViewCode = () => {
  codeDialogOpen.value = true;
};

const handleTogglePin = (itemId: string) => {
  togglePinContextItem(itemId);
};

const handleRemoveContextItem = (itemId: string) => {
  removeContextItem(itemId);
  toast({
    title: '已移除',
    description: '上下文项目已移除',
  });
};

const handleClearUnpinned = () => {
  const unpinnedCount = activeContextItems.value.filter(item => !item.pinned).length;
  clearUnpinnedItems();
  toast({
    title: '已清除',
    description: `已移除 ${unpinnedCount} 个非固定项目`,
  });
};

const handleAddFile = (file: { id: string; name: string; path: string; tokens?: number }) => {
  const newItem: ContextItem = {
    id: file.id,
    type: 'file',
    name: file.name,
    path: file.path,
    tokens: file.tokens || 500,
    pinned: false,
    addedAt: new Date(),
    priority: 5,
  };
  addContextItem(newItem);
  toast({
    title: '已添加',
    description: `${file.name} 已添加到上下文`,
  });
};

const handleRemoveFile = (fileId: string) => {
  removeContextItem(fileId);
};

const handleCompress = (strategy: CompressionStrategy, options?: CompressionOptions) => {
  const result = compressContext(activeContextItems.value, strategy, options);
  setAllContextItems(result.remainingItems);

  const newContextSize = result.remainingItems.reduce((sum, item) => sum + item.tokens, 0);
  updateSession({ contextSize: newContextSize });

  toast({
    title: '压缩完成',
    description: `已释放 ${result.savedTokens.toLocaleString()} tokens`,
  });
};

const handleLoadMore = async () => {
  if (loadingHistory.value || !hasMore.value || isLoadingMore.value) return;

  // 标记正在加载更多
  isLoadingMore.value = true;

  // 保存当前滚动位置
  const container = messagesContainerRef.value;
  const oldScrollHeight = container?.scrollHeight || 0;

  await loadSessionHistory(true);

  // 直接将新加载的消息插入到消息列表前面，而不是调用 addMessage
  if (apiMessages.value.length > 0) {
    messages.value = [...apiMessages.value, ...messages.value];
  }

  // 恢复滚动位置（保持在原来的消息位置）
  await nextTick();
  if (container) {
    const newScrollHeight = container.scrollHeight;
    container.scrollTop = newScrollHeight - oldScrollHeight;
  }

  // 重置标志
  isLoadingMore.value = false;
};

// 滚动事件处理
const handleScroll = () => {
  const container = messagesContainerRef.value;
  if (!container || loadingHistory.value || !hasMore.value) return;

  // 检测是否滚动到顶部（距离顶部小于 100px）
  if (container.scrollTop < 100) {
    handleLoadMore();
  }
};

const handleQuestionSubmit = (answers: any) => {
  submitAnswers(answers);
};
</script>
