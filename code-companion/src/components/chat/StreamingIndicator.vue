<template>
  <div v-if="status !== 'idle'" :class="['flex items-center gap-1.5 text-[10px]', config.color, className]">
    <component :is="config.icon" class="w-3 h-3" :class="config.spinClass" />
    <span>{{ config.text }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, toRefs } from 'vue';
import { Loader2, Pause, AlertCircle, CheckCircle2, Wifi, WifiOff } from 'lucide-vue-next';
import { StreamingStatus } from '@/composables/useStreaming';

const props = defineProps<{ status: StreamingStatus; className?: string }>();
const { className } = toRefs(props);

const config = computed(() => {
  switch (props.status) {
    case 'connecting':
      return { icon: Wifi, text: '连接中...', color: 'text-muted-foreground', spinClass: 'animate-pulse' };
    case 'connected':
      return { icon: Wifi, text: '已连接', color: 'text-primary', spinClass: '' };
    case 'streaming':
      return { icon: Loader2, text: '生成中...', color: 'text-primary', spinClass: 'animate-spin' };
    case 'interrupted':
      return { icon: Pause, text: '已中断', color: 'text-warning', spinClass: '' };
    case 'completed':
      return { icon: CheckCircle2, text: '完成', color: 'text-green-500', spinClass: '' };
    case 'error':
      return { icon: AlertCircle, text: '连接错误', color: 'text-destructive', spinClass: '' };
    default:
      return { icon: WifiOff, text: '未连接', color: 'text-muted-foreground', spinClass: '' };
  }
});
</script>
