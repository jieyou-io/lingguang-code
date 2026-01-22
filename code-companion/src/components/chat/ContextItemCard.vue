<template>
  <div
    :class="[
      'flex items-center gap-3 p-2.5 rounded-lg border transition-all',
      item.pinned
        ? 'bg-primary/5 border-primary/30'
        : 'bg-secondary/30 border-border hover:bg-secondary/50'
    ]"
  >
    <div
      :class="[
        'flex items-center justify-center w-8 h-8 rounded-md',
        item.pinned ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'
      ]"
    >
      <component :is="typeIcons[item.type]" class="w-4 h-4" />
    </div>

    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2">
        <span class="text-sm font-medium truncate">{{ item.name }}</span>
        <span class="text-[10px] text-muted-foreground px-1.5 py-0.5 rounded bg-muted">
          {{ typeLabels[item.type] }}
        </span>
      </div>
      <div class="flex items-center gap-2 mt-0.5">
        <span class="text-xs text-muted-foreground">
          {{ item.tokens.toLocaleString() }} tokens
        </span>
        <div class="w-12 h-1 bg-muted rounded-full overflow-hidden">
          <div class="h-full bg-primary rounded-full" :style="{ width: `${percent}%` }" />
        </div>
        <span class="text-[10px] text-muted-foreground">{{ percent }}%</span>
      </div>
    </div>

    <div class="flex items-center gap-1">
      <button
        class="p-1.5 rounded hover:bg-muted transition-colors"
        :title="item.pinned ? '取消固定' : '固定'"
        @click="onTogglePin(item.id)"
      >
        <PinOff v-if="item.pinned" class="w-3.5 h-3.5 text-primary" />
        <Pin v-else class="w-3.5 h-3.5 text-muted-foreground" />
      </button>
      <button
        class="p-1.5 rounded hover:bg-destructive/20 transition-colors"
        title="移除"
        @click="onRemove(item.id)"
      >
        <X class="w-3.5 h-3.5 text-muted-foreground hover:text-destructive" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import {
  FileCode,
  MessageSquare,
  History,
  Puzzle,
  Settings,
  Pin,
  PinOff,
  X,
} from 'lucide-vue-next';
import { ContextItem } from '@/types';

const props = defineProps<{
  item: ContextItem;
  totalTokens: number;
  onTogglePin: (itemId: string) => void;
  onRemove: (itemId: string) => void;
}>();

const typeIcons = {
  file: FileCode,
  selection: MessageSquare,
  history: History,
  plugin: Puzzle,
  system: Settings,
};

const typeLabels = {
  file: '文件',
  selection: '选区',
  history: '历史',
  plugin: '插件',
  system: '系统',
};

const percent = computed(() =>
  props.totalTokens > 0
    ? Math.round((props.item.tokens / props.totalTokens) * 100)
    : 0
);

const onTogglePin = props.onTogglePin;
const onRemove = props.onRemove;
</script>
