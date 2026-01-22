<template>
  <div :class="[sizeClasses[size], colors[engine], className, 'rounded-md border flex items-center justify-center font-mono font-semibold']">
    {{ labels[engine] }}
  </div>
</template>

<script setup lang="ts">
import { toRefs } from 'vue';
import { AIEngine } from '@/types';

const props = withDefaults(defineProps<{
  engine: AIEngine;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}>(), {
  size: 'md',
  className: '',
});

const sizeClasses = {
  sm: 'w-4 h-4 text-xs',
  md: 'w-6 h-6 text-sm',
  lg: 'w-8 h-8 text-base',
};

const colors: Record<AIEngine, string> = {
  claude: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  codex: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  gemini: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
};

const labels: Record<AIEngine, string> = {
  claude: 'C',
  codex: 'X',
  gemini: 'G',
};

const { size, engine, className } = toRefs(props);
</script>
