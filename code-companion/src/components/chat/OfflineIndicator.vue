<template>
  <div v-if="!online || checkpoint" class="px-4 py-2 border-b border-border/50">
    <div v-if="!online" class="flex items-center gap-2 text-amber-400 text-sm">
      <WifiOff class="w-4 h-4" />
      <span>离线模式 - 消息将在恢复连接后同步</span>
    </div>

    <div v-if="checkpoint && checkpoint.status === 'interrupted'" class="flex items-center justify-between">
      <div class="flex items-center gap-2 text-muted-foreground text-sm">
        <RefreshCw class="w-4 h-4" />
        <span>检测到未完成的回复</span>
      </div>
      <button @click="onResume" class="text-sm text-primary hover:text-primary/80 font-medium">
        继续
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { WifiOff, RefreshCw } from 'lucide-vue-next';
import { SessionCheckpoint } from '@/lib/sessionStorage';

defineProps<{
  online: boolean;
  checkpoint?: SessionCheckpoint | null;
  onResume?: () => void;
}>();
</script>
