<template>
  <div class="relative group">
    <button
      class="w-full text-left p-4 rounded-lg border transition-all duration-200 active:scale-[0.98] animate-slide-up"
      :class="selected ? 'bg-primary/10 border-primary/50' : 'bg-card border-border hover:border-primary/30 hover:bg-card/80'"
      @click="onClick"
    >
      <div class="flex items-start gap-3">
        <div
          class="w-10 h-10 rounded-lg flex items-center justify-center"
          :class="selected ? 'bg-primary text-primary-foreground' : 'bg-secondary'"
        >
          <FolderOpen class="w-5 h-5" />
        </div>

        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between mb-1">
            <h3 class="font-semibold text-sm truncate">{{ project.name }}</h3>
            <ChevronRight class="w-4 h-4 text-muted-foreground flex-shrink-0" />
          </div>

          <p class="text-xs text-muted-foreground truncate mb-2">
            {{ project.path }}
          </p>

          <div class="flex items-center gap-4 text-xs text-muted-foreground">
            <span class="flex items-center gap-1">
              <MessageSquare class="w-3 h-3" />
              {{ project.activeSessions }} 活跃
            </span>
            <span class="flex items-center gap-1 text-accent">
              <Coins class="w-3 h-3" />
              ${{ project.totalCost.toFixed(2) }}
            </span>
          </div>
        </div>
      </div>
    </button>

    <div class="absolute top-2 right-8 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      <button
        v-if="onBindNotification"
        class="p-2 rounded-lg bg-secondary text-muted-foreground hover:bg-secondary/80 transition-colors"
        title="绑定机器人通知"
        @click.stop="onBindNotification"
      >
        <Bell class="w-4 h-4" />
      </button>
      <button
        v-if="onViewCode"
        class="p-2 rounded-lg bg-secondary text-muted-foreground hover:bg-secondary/80 transition-colors"
        title="查看代码文件"
        @click.stop="onViewCode"
      >
        <FileCode class="w-4 h-4" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { FolderOpen, MessageSquare, Coins, ChevronRight, Bell, FileCode } from 'lucide-vue-next';
import { Project } from '@/types';

defineProps<{
  project: Project;
  onClick: () => void;
  selected?: boolean;
  onBindNotification?: () => void;
  onViewCode?: () => void;
}>();
</script>
