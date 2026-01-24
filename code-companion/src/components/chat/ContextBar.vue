<template>
  <div class="border-b border-border">
    <div class="flex items-center justify-between px-4 py-2">
      <div class="flex items-center gap-3">
        <EngineSelector
          :engine="session.engine"
          :on-change="handleEngineChange"
          :disabled="disabled"
        />
        <span class="text-xs text-muted-foreground">{{ session.tokenCount.toLocaleString() }} tokens</span>
        <span class="text-xs text-accent">${{ session.cost.toFixed(2) }}</span>
        <span v-if="model" class="text-xs text-primary font-medium">{{ model }}</span>
        <span v-if="thinkingEnabled" class="flex items-center gap-0.5 text-xs text-primary">
          <Brain class="w-3 h-3" />
        </span>
        <span v-if="planModeEnabled" class="flex items-center gap-0.5 text-xs text-primary">
          <ListChecks class="w-3 h-3" />
        </span>

        <!-- 全局统计数据 -->
        <div v-if="quickStats" class="flex items-center gap-2 ml-2 pl-2 border-l border-border">
          <span class="text-[10px] text-muted-foreground">今日:</span>
          <span class="text-xs text-primary font-medium">{{ formatTokens(quickStats.today.tokens) }}</span>
          <span class="text-xs text-accent">${{ quickStats.today.cost.toFixed(2) }}</span>
          <span class="text-[10px] text-muted-foreground ml-1">本周:</span>
          <span class="text-xs text-muted-foreground">{{ quickStats.week.sessions }} 会话</span>
        </div>
      </div>
      <button
        class="flex items-center gap-2 hover:bg-secondary/50 px-2 py-1 rounded transition-colors"
        @click="expanded = !expanded"
      >
        <div class="flex items-center gap-1.5">
          <div class="w-16 h-1 bg-secondary rounded-full overflow-hidden">
            <div
              class="h-full rounded-full"
              :class="contextPercent > 80 ? 'bg-accent' : 'bg-primary'"
              :style="{ width: `${Math.min(contextPercent, 100)}%` }"
            />
          </div>
          <span class="text-[10px] text-muted-foreground">{{ contextPercent }}%</span>
        </div>
        <ChevronDown class="w-4 h-4 text-muted-foreground transition-transform" :class="expanded ? 'rotate-180' : ''" />
      </button>
    </div>

    <div v-if="expanded" class="px-4 pb-3 space-y-3 animate-slide-up">
      <div class="grid grid-cols-3 gap-3">
        <div class="p-2.5 rounded-lg bg-secondary/50 border border-border">
          <div class="flex items-center gap-1.5 mb-1">
            <Zap class="w-3 h-3 text-primary" />
            <span class="text-[10px] text-muted-foreground">引擎</span>
          </div>
          <p class="text-xs font-medium capitalize">{{ session.engine }}</p>
        </div>
        <div class="p-2.5 rounded-lg bg-secondary/50 border border-border">
          <div class="flex items-center gap-1.5 mb-1">
            <FileCode class="w-3 h-3 text-primary" />
            <span class="text-[10px] text-muted-foreground">上下文</span>
          </div>
          <p class="text-xs font-medium">
            {{ Math.round(totalContextTokens / 1000) }}K / {{ Math.round(session.maxContext / 1000) }}K
          </p>
        </div>
        <div class="p-2.5 rounded-lg bg-secondary/50 border border-border">
          <div class="flex items-center gap-1.5 mb-1">
            <Coins class="w-3 h-3 text-accent" />
            <span class="text-[10px] text-muted-foreground">成本</span>
          </div>
          <p class="text-xs font-medium text-accent">${{ session.cost.toFixed(2) }}</p>
        </div>
      </div>

      <div class="border border-border rounded-lg p-3 max-h-64 overflow-y-auto">
        <ContextItemList
          :items="contextItems"
          :on-toggle-pin="onTogglePin"
          :on-remove="onRemoveItem"
          :on-clear-unpinned="onClearUnpinned"
        />
      </div>

      <div class="flex gap-2">
        <button
          class="flex-1 flex items-center justify-center gap-1.5 py-2 text-xs rounded-lg border border-border hover:bg-secondary/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="contextItems.length === 0"
          @click="compressionDialogOpen = true"
        >
          <Minimize2 class="w-3.5 h-3.5" />
          压缩上下文
        </button>
        <button
          class="flex-1 flex items-center justify-center gap-1.5 py-2 text-xs rounded-lg border border-border hover:bg-secondary/50 transition-colors"
          @click="fileManagerOpen = true"
        >
          <FolderOpen class="w-3.5 h-3.5" />
          管理文件
        </button>
      </div>
    </div>
  </div>

  <FileManagerSheet
    :open="fileManagerOpen"
    :on-open-change="(value) => (fileManagerOpen = value)"
    :context-items="contextItems"
    :file-tree="fileTree"
    :on-add-file="handleAddFile"
    :on-remove-file="handleRemoveFile"
  />

  <ContextCompressionDialog
    :open="compressionDialogOpen"
    :on-open-change="(value) => (compressionDialogOpen = value)"
    :context-items="contextItems"
    :on-compress="handleCompress"
  />
</template>

<script setup lang="ts">
import { computed, ref, toRefs, onMounted } from 'vue';
import { ChevronDown, FileCode, Zap, Coins, Minimize2, FolderOpen, Brain, ListChecks } from 'lucide-vue-next';
import { Session, AIEngine, AIModel, ContextItem, ProjectFileNode } from '@/types';
import EngineSelector from './EngineSelector.vue';
import ContextItemList from './ContextItemList.vue';
import FileManagerSheet from './FileManagerSheet.vue';
import ContextCompressionDialog, { CompressionStrategy, CompressionOptions } from './ContextCompressionDialog.vue';
import { getQuickStats, type QuickStatsResponse } from '@/lib/usage-api';

const props = defineProps<{
  session: Session;
  contextItems: ContextItem[];
  fileTree?: ProjectFileNode[];
  model?: AIModel;
  thinkingEnabled?: boolean;
  planModeEnabled?: boolean;
  onEngineChange?: (engine: AIEngine) => void;
  onTogglePin?: (itemId: string) => void;
  onRemoveItem?: (itemId: string) => void;
  onClearUnpinned?: () => void;
  onAddFile?: (file: { id: string; name: string; path: string; tokens?: number }) => void;
  onRemoveFile?: (fileId: string) => void;
  onCompress?: (strategy: CompressionStrategy, options?: CompressionOptions) => void;
  disabled?: boolean;
}>();

const expanded = ref(false);
const fileManagerOpen = ref(false);
const compressionDialogOpen = ref(false);
const quickStats = ref<QuickStatsResponse | null>(null);

const { session, contextItems, model, thinkingEnabled, planModeEnabled, disabled } = toRefs(props);

// 加载快速统计数据
const loadQuickStats = async () => {
  try {
    quickStats.value = await getQuickStats();
  } catch (error) {
    console.error('Failed to load quick stats:', error);
  }
};

// 格式化 token 数量
const formatTokens = (tokens: number): string => {
  if (tokens >= 1_000_000) {
    return `${(tokens / 1_000_000).toFixed(1)}M`;
  } else if (tokens >= 1_000) {
    return `${(tokens / 1_000).toFixed(1)}K`;
  }
  return tokens.toString();
};

// 组件挂载时加载统计数据
onMounted(() => {
  loadQuickStats();
});

const totalContextTokens = computed(() =>
  contextItems.value.reduce((sum, item) => sum + item.tokens, 0)
);

const contextPercent = computed(() =>
  session.value.maxContext > 0
    ? Math.round((totalContextTokens.value / session.value.maxContext) * 100)
    : 0
);

const handleEngineChange = (engine: AIEngine) => {
  props.onEngineChange?.(engine);
};

const handleAddFile = (file: { id: string; name: string; path: string; tokens?: number }) => {
  props.onAddFile?.(file);
};

const handleRemoveFile = (fileId: string) => {
  props.onRemoveFile?.(fileId);
};

const handleCompress = (strategy: CompressionStrategy, options?: CompressionOptions) => {
  props.onCompress?.(strategy, options);
};

const onTogglePin = props.onTogglePin || (() => undefined);
const onRemoveItem = props.onRemoveItem || (() => undefined);
const onClearUnpinned = props.onClearUnpinned || (() => undefined);
</script>
