<template>
  <div v-if="items.length === 0" class="text-center py-6 text-muted-foreground">
    <Layers class="w-8 h-8 mx-auto mb-2 opacity-50" />
    <p class="text-sm">暂无上下文项目</p>
    <p class="text-xs mt-1">添加文件或发送消息以构建上下文</p>
  </div>

  <div v-else class="space-y-3">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span class="text-xs text-muted-foreground">
          共 {{ items.length }} 项 · {{ totalTokens.toLocaleString() }} tokens
        </span>
      </div>
      <button
        v-if="unpinnedCount > 0"
        class="flex items-center gap-1 text-xs text-muted-foreground hover:text-destructive transition-colors"
        @click="onClearUnpinned"
      >
        <Trash2 class="w-3 h-3" />
        清除非固定 ({{ unpinnedCount }})
      </button>
    </div>

    <div class="flex gap-1 overflow-x-auto pb-1">
      <button
        v-for="filterItem in filters"
        :key="filterItem.key"
        :class="[
          'px-2.5 py-1 text-xs rounded-full whitespace-nowrap transition-colors',
          filter === filterItem.key
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-muted-foreground hover:bg-muted/80'
        ]"
        @click="filter = filterItem.key"
      >
        {{ filterItem.label }}
      </button>
    </div>

    <div v-if="pinnedItems.length > 0" class="space-y-2">
      <div class="flex items-center gap-1.5 text-xs text-primary">
        <Pin class="w-3 h-3" />
        <span>已固定 ({{ pinnedItems.length }})</span>
      </div>
      <div class="space-y-1.5">
        <ContextItemCard
          v-for="item in pinnedItems"
          :key="item.id"
          :item="item"
          :total-tokens="totalTokens"
          :on-toggle-pin="onTogglePin"
          :on-remove="onRemove"
        />
      </div>
    </div>

    <div v-if="unpinnedItems.length > 0" class="space-y-2">
      <div v-if="pinnedItems.length > 0" class="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Layers class="w-3 h-3" />
        <span>其他 ({{ unpinnedItems.length }})</span>
      </div>
      <div class="space-y-1.5">
        <ContextItemCard
          v-for="item in unpinnedItems"
          :key="item.id"
          :item="item"
          :total-tokens="totalTokens"
          :on-toggle-pin="onTogglePin"
          :on-remove="onRemove"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { Pin, Layers, Trash2 } from 'lucide-vue-next';
import { ContextItem } from '@/types';
import ContextItemCard from './ContextItemCard.vue';

const props = defineProps<{
  items: ContextItem[];
  onTogglePin: (itemId: string) => void;
  onRemove: (itemId: string) => void;
  onClearUnpinned: () => void;
}>();

type FilterType = 'all' | 'file' | 'selection' | 'history' | 'plugin' | 'system';

const filter = ref<FilterType>('all');

const filters: { key: FilterType; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'file', label: '文件' },
  { key: 'history', label: '历史' },
  { key: 'selection', label: '选区' },
  { key: 'plugin', label: '插件' },
];

const filteredItems = computed(() =>
  filter.value === 'all'
    ? props.items
    : props.items.filter(item => item.type === filter.value)
);

const pinnedItems = computed(() => filteredItems.value.filter(item => item.pinned));
const unpinnedItems = computed(() => filteredItems.value.filter(item => !item.pinned));
const totalTokens = computed(() => props.items.reduce((sum, item) => sum + item.tokens, 0));
const unpinnedCount = computed(() => props.items.filter(item => !item.pinned).length);

const onTogglePin = props.onTogglePin;
const onRemove = props.onRemove;
const onClearUnpinned = props.onClearUnpinned;
</script>
