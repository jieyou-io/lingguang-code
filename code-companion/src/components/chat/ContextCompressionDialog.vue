<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div class="bg-background rounded-lg p-6 max-w-lg w-full m-4">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold">压缩上下文</h2>
        <button class="text-muted-foreground hover:text-foreground" @click="close">×</button>
      </div>

      <div class="space-y-6">
        <div class="flex items-center justify-between p-3 rounded-lg bg-muted/50">
          <div>
            <p class="text-sm text-muted-foreground">当前上下文</p>
            <p class="text-lg font-semibold">{{ totalTokens.toLocaleString() }} tokens</p>
          </div>
          <ArrowRight class="w-5 h-5 text-muted-foreground" />
          <div class="text-right">
            <p class="text-sm text-muted-foreground">压缩后预估</p>
            <p class="text-lg font-semibold text-primary">
              {{ result.remainingTokens.toLocaleString() }} tokens
            </p>
          </div>
        </div>

        <div class="space-y-3">
          <div
            v-for="strategy in strategies"
            :key="strategy.id"
            :class="[
              'flex items-start gap-3 p-3 rounded-lg border transition-colors cursor-pointer',
              selectedStrategy === strategy.id
                ? 'border-primary bg-primary/5'
                : 'border-border hover:bg-muted/50',
              isDisabled(strategy.id) ? 'opacity-50 cursor-not-allowed' : ''
            ]"
            @click="selectStrategy(strategy.id)"
          >
            <input
              type="radio"
              :value="strategy.id"
              :checked="selectedStrategy === strategy.id"
              class="mt-1 accent-primary"
              :disabled="isDisabled(strategy.id)"
            />
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <component :is="strategy.icon" class="w-4 h-4 text-primary" />
                <span class="text-sm font-medium">{{ strategy.title }}</span>
              </div>
              <p class="text-xs text-muted-foreground mt-1">{{ strategy.description }}</p>
            </div>
          </div>
        </div>

        <div v-if="selectedStrategy === 'remove-old'" class="space-y-3 p-3 rounded-lg bg-muted/30">
          <div class="flex items-center justify-between">
            <label class="text-sm">保留最近消息数</label>
            <span class="text-sm font-medium">{{ keepRecentCount }} 条</span>
          </div>
          <input
            type="range"
            min="1"
            :max="Math.max(historyCount, 20)"
            step="1"
            v-model.number="keepRecentCount"
            class="w-full"
          />
        </div>

        <div v-if="selectedStrategy === 'custom'" class="space-y-3 p-3 rounded-lg bg-muted/30">
          <div class="flex items-center justify-between">
            <label class="text-sm">目标大小</label>
            <span class="text-sm font-medium">{{ targetTokenPercent }}%</span>
          </div>
          <input
            type="range"
            min="10"
            max="90"
            step="5"
            v-model.number="targetTokenPercent"
            class="w-full"
          />
          <p class="text-xs text-muted-foreground">
            目标: {{ Math.floor(totalTokens * (targetTokenPercent / 100)).toLocaleString() }} tokens
          </p>
        </div>

        <div class="flex items-center justify-between text-sm p-3 rounded-lg bg-destructive/10 border border-destructive/20">
          <span class="text-destructive">将释放</span>
          <span class="font-semibold text-destructive">
            {{ result.removedTokens.toLocaleString() }} tokens
            ({{ totalTokens > 0 ? Math.round((result.removedTokens / totalTokens) * 100) : 0 }}%)
          </span>
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 mt-6">
        <button class="px-3 py-2 text-sm rounded-md border border-border hover:bg-muted" @click="close">
          取消
        </button>
        <button class="px-3 py-2 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90" @click="handleCompress">
          确认压缩
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { Sparkles, History, PinOff, Settings2, ArrowRight } from 'lucide-vue-next';
import { ContextItem } from '@/types';

export type CompressionStrategy = 'smart' | 'remove-old' | 'remove-unpinned' | 'custom';

export interface CompressionOptions {
  keepRecentCount?: number;
  targetTokens?: number;
}

const props = defineProps<{
  open: boolean;
  onOpenChange: (open: boolean) => void;
  contextItems: ContextItem[];
  onCompress: (strategy: CompressionStrategy, options?: CompressionOptions) => void;
}>();

const selectedStrategy = ref<CompressionStrategy>('smart');
const keepRecentCount = ref(10);
const targetTokenPercent = ref(50);

const strategies = [
  { id: 'smart', icon: Sparkles, title: '智能压缩', description: 'AI 自动识别并摘要非核心内容' },
  { id: 'remove-old', icon: History, title: '移除旧历史', description: '保留最近的对话，移除较早的历史' },
  { id: 'remove-unpinned', icon: PinOff, title: '清除非固定项', description: '移除所有未固定的上下文项目' },
  { id: 'custom', icon: Settings2, title: '自定义', description: '设置目标 token 数量进行压缩' },
] as const;

const totalTokens = computed(() => props.contextItems.reduce((sum, item) => sum + item.tokens, 0));
const pinnedTokens = computed(() => props.contextItems.filter(item => item.pinned).reduce((sum, item) => sum + item.tokens, 0));
const unpinnedCount = computed(() => props.contextItems.filter(item => !item.pinned).length);
const historyCount = computed(() => props.contextItems.filter(item => item.type === 'history').length);

const isDisabled = (strategy: CompressionStrategy) => {
  if (strategy === 'remove-old') return historyCount.value === 0;
  if (strategy === 'remove-unpinned') return unpinnedCount.value === 0;
  return false;
};

const estimateResult = () => {
  switch (selectedStrategy.value) {
    case 'smart':
      return {
        removedTokens: Math.floor(totalTokens.value * 0.4),
        remainingTokens: Math.ceil(totalTokens.value * 0.6),
      };
    case 'remove-old': {
      const historyItems = props.contextItems
        .filter(item => item.type === 'history')
        .sort((a, b) => new Date(b.addedAt).getTime() - new Date(a.addedAt).getTime());
      const toRemove = historyItems.slice(keepRecentCount.value);
      const removedTokens = toRemove.reduce((sum, item) => sum + item.tokens, 0);
      return { removedTokens, remainingTokens: totalTokens.value - removedTokens };
    }
    case 'remove-unpinned': {
      const unpinnedTokens = totalTokens.value - pinnedTokens.value;
      return { removedTokens: unpinnedTokens, remainingTokens: pinnedTokens.value };
    }
    case 'custom': {
      const targetTokens = Math.floor(totalTokens.value * (targetTokenPercent.value / 100));
      return { removedTokens: totalTokens.value - targetTokens, remainingTokens: targetTokens };
    }
    default:
      return { removedTokens: 0, remainingTokens: totalTokens.value };
  }
};

const result = computed(() => estimateResult());

const selectStrategy = (strategy: CompressionStrategy) => {
  if (isDisabled(strategy)) return;
  selectedStrategy.value = strategy;
};

const handleCompress = () => {
  const options: CompressionOptions = {};
  if (selectedStrategy.value === 'remove-old') {
    options.keepRecentCount = keepRecentCount.value;
  } else if (selectedStrategy.value === 'custom') {
    options.targetTokens = Math.floor(totalTokens.value * (targetTokenPercent.value / 100));
  }

  props.onCompress(selectedStrategy.value, options);
  props.onOpenChange(false);
};

const close = () => props.onOpenChange(false);
</script>
