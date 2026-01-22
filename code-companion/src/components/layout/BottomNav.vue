<template>
  <nav class="fixed bottom-0 left-0 right-0 z-50 glass border-t border-border safe-area-bottom">
    <div class="flex items-center justify-around h-16 px-2">
      <button
        v-for="item in navItems"
        :key="item.path"
        @click="router.push(item.path)"
        :class="[
          'flex flex-col items-center justify-center gap-1 py-2 px-4 rounded-lg',
          'transition-all duration-200 min-w-[56px]',
          isActive(item.path)
            ? 'text-primary'
            : 'text-muted-foreground hover:text-foreground'
        ]"
      >
        <component
          :is="item.icon"
          :class="['w-5 h-5', isActive(item.path) ? 'stroke-[2.5]' : '']"
        />
        <span :class="['text-[10px] font-medium', isActive(item.path) ? 'text-primary' : '']">
          {{ item.label }}
        </span>
      </button>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  MessageSquare,
  FolderOpen,
  BarChart3,
  Puzzle,
  Settings
} from 'lucide-vue-next';

const route = useRoute();
const router = useRouter();

const navItems = [
  { path: '/sessions', icon: MessageSquare, label: '会话' },
  { path: '/projects', icon: FolderOpen, label: '项目' },
  { path: '/stats', icon: BarChart3, label: '统计' },
  { path: '/plugins', icon: Puzzle, label: 'MCP' },
  { path: '/settings', icon: Settings, label: '设置' },
];

const isActive = (path: string) => {
  if (path === '/sessions') {
    return route.path === '/' || route.path.startsWith('/session') || route.path.startsWith('/chat');
  }
  return route.path.startsWith(path);
};
</script>
