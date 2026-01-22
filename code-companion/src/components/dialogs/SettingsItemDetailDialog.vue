<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
    @click.self="handleClose"
  >
    <div
      class="w-full max-w-2xl max-h-[80vh] overflow-y-auto bg-background rounded-lg shadow-xl border border-border"
      @click.stop
    >
      <!-- Header -->
      <div class="sticky top-0 bg-background border-b border-border px-6 py-4">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold">{{ title }}</h2>
          <button
            @click="handleClose"
            class="p-2 rounded-lg hover:bg-secondary transition-colors"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Content -->
      <div class="px-6 py-4 space-y-4">
        <!-- ID -->
        <div>
          <label class="text-sm font-medium text-muted-foreground">ID</label>
          <p class="text-sm mt-1">{{ item?.id }}</p>
        </div>

        <!-- 路径 -->
        <div>
          <label class="text-sm font-medium text-muted-foreground">路径</label>
          <p class="text-sm mt-1 font-mono text-xs bg-secondary px-2 py-1 rounded">{{ item?.path }}</p>
        </div>

        <!-- 启用状态 -->
        <div>
          <label class="text-sm font-medium text-muted-foreground">状态</label>
          <p class="text-sm mt-1">
            <span
              class="inline-flex items-center px-2 py-1 rounded text-xs"
              :class="item?.enabled ? 'bg-green-500/10 text-green-500' : 'bg-gray-500/10 text-gray-500'"
            >
              {{ item?.enabled ? '已启用' : '已禁用' }}
            </span>
          </p>
        </div>

        <!-- Metadata (仅 Agent 和 Skill) -->
        <template v-if="itemType !== 'plugin'">
          <!-- Name (Agent) -->
          <div v-if="itemType === 'agent' && item?.metadata?.name">
            <label class="text-sm font-medium text-muted-foreground">名称</label>
            <p class="text-sm mt-1">{{ item.metadata.name }}</p>
          </div>

          <!-- Description -->
          <div v-if="item?.metadata?.description">
            <label class="text-sm font-medium text-muted-foreground">描述</label>
            <p class="text-sm mt-1">{{ item.metadata.description }}</p>
          </div>

          <!-- Tools (Agent) -->
          <div v-if="itemType === 'agent' && item?.metadata?.tools && item.metadata.tools.length > 0">
            <label class="text-sm font-medium text-muted-foreground">工具</label>
            <div class="flex flex-wrap gap-1 mt-1">
              <span
                v-for="tool in item.metadata.tools"
                :key="tool"
                class="px-2 py-1 text-xs bg-blue-500/10 text-blue-500 rounded"
              >
                {{ tool }}
              </span>
            </div>
          </div>

          <!-- Content -->
          <div v-if="item?.content">
            <label class="text-sm font-medium text-muted-foreground">内容</label>
            <div class="mt-1 text-sm bg-secondary p-3 rounded-lg max-h-96 overflow-y-auto">
              <pre class="whitespace-pre-wrap font-mono text-xs">{{ item.content }}</pre>
            </div>
          </div>
        </template>
      </div>

      <!-- Footer -->
      <div class="sticky bottom-0 bg-background border-t border-border px-6 py-4">
        <div class="flex justify-end">
          <button
            class="px-4 py-2 text-sm rounded-lg bg-secondary text-foreground hover:bg-secondary/80 transition-colors"
            @click="handleClose"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { X } from 'lucide-vue-next';
import type { Plugin, Agent, Skill } from '@/lib/settings-api';

interface Props {
  open: boolean;
  item: Plugin | Agent | Skill | null;
  itemType: 'plugin' | 'agent' | 'skill';
}

interface Emits {
  (e: 'update:open', value: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const handleClose = () => {
  emit('update:open', false);
};

const title = computed(() => {
  if (!props.item) return '';

  switch (props.itemType) {
    case 'plugin':
      return `插件详情 - ${props.item.id}`;
    case 'agent':
      return `代理详情 - ${(props.item as Agent).metadata?.name || props.item.id}`;
    case 'skill':
      return `技能详情 - ${(props.item as Skill).metadata?.description || props.item.id}`;
    default:
      return '详情';
  }
});
</script>
