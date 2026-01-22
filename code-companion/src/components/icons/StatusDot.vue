<template>
  <span class="relative flex items-center justify-center">
    <span
      v-if="pulse && status === 'active'"
      :class="['absolute rounded-full pulse-ring', sizeClasses[size], colors[status]]"
    />
    <span :class="[sizeClasses[size], 'rounded-full', colors[status]]" />
  </span>
</template>

<script setup lang="ts">
import { toRefs } from 'vue';

const props = withDefaults(defineProps<{
  status: 'active' | 'paused' | 'completed' | 'error';
  pulse?: boolean;
  size?: 'sm' | 'md';
}>(), {
  pulse: true,
  size: 'md',
});

const colors = {
  active: 'bg-success',
  paused: 'bg-accent',
  completed: 'bg-muted-foreground',
  error: 'bg-destructive',
};

const sizeClasses = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
};

const { status, pulse, size } = toRefs(props);
</script>
