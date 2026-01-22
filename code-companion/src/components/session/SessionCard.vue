<template>
  <div
    class="p-4 rounded-lg bg-card border border-border hover:border-primary/50 transition-colors cursor-pointer"
    @click="$emit('click')"
  >
    <div class="flex items-start justify-between mb-2">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1">
          <h3 class="font-medium truncate">{{ session.title }}</h3>
          <span
            :class="[
              'px-1.5 py-0.5 rounded text-[10px] font-medium',
              engineClasses[session.engine] || ''
            ]"
          >
            {{ engineText[session.engine] }}
          </span>
        </div>
        <p class="text-xs text-muted-foreground">
          {{ formatDate(session.updatedAt) }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <span
          :class="[
            'px-2 py-0.5 rounded text-xs',
            statusClasses[session.status] || ''
          ]"
        >
          {{ statusText[session.status] }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Session } from '@/types';

defineProps<{
  session: Session;
}>();

defineEmits<{
  click: [];
  delete: [];
  'view-code': [];
}>();

const statusText: Record<string, string> = {
  active: '活跃',
  paused: '已暂停',
  completed: '已完成',
  error: '错误',
};

const statusClasses: Record<string, string> = {
  active: 'bg-success/20 text-success',
  paused: 'bg-muted text-muted-foreground',
  completed: 'bg-muted text-muted-foreground',
  error: 'bg-destructive/20 text-destructive',
};

const engineText: Record<string, string> = {
  claude: 'Claude',
  codex: 'Codex',
  gemini: 'Gemini',
};

const engineClasses: Record<string, string> = {
  claude: 'bg-blue-500/20 text-blue-600 dark:text-blue-400',
  codex: 'bg-green-500/20 text-green-600 dark:text-green-400',
  gemini: 'bg-purple-500/20 text-purple-600 dark:text-purple-400',
};

const formatDate = (date: Date) => {
  return new Date(date).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatNumber = (num: number) => {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
};
</script>
