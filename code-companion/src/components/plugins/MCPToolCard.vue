<template>
  <div class="p-4 rounded-lg bg-card border border-border animate-slide-up">
    <div class="flex items-start gap-3">
      <div class="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center text-xl">
        {{ icon }}
      </div>

      <div class="flex-1 min-w-0">
        <h3 class="font-medium text-sm mb-1">{{ tool.name }}</h3>
        <p class="text-xs text-muted-foreground line-clamp-2">{{ description }}</p>
      </div>

      <label class="inline-flex items-center">
        <input
          type="checkbox"
          class="accent-primary"
          :checked="tool.isActive"
          @change="onToggle(($event.target as HTMLInputElement).checked)"
        />
      </label>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { MCPServer } from '@/types/mcp';

const props = defineProps<{
  tool: MCPServer;
  onToggle: (enabled: boolean) => void;
}>();

// 根据传输协议生成图标
const icon = computed(() => {
  if (props.tool.transport === 'stdio') return '📡';
  if (props.tool.transport === 'sse') return '🌐';
  return '🔧';
});

// 生成描述信息
const description = computed(() => {
  const parts = [];
  parts.push(`传输: ${props.tool.transport}`);
  if (props.tool.command) parts.push(`命令: ${props.tool.command}`);
  if (props.tool.url) parts.push(`URL: ${props.tool.url}`);
  return parts.join(' | ');
});
</script>
