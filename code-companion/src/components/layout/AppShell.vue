<template>
  <div class="min-h-screen bg-background flex flex-col">
    <main :class="['flex-1', { 'pb-20': !hideNav }]">
      <slot />
    </main>
    <BottomNav v-if="!hideNav" />
  </div>
</template>

<script setup lang="ts">
import BottomNav from './BottomNav.vue';

defineProps<{
  hideNav?: boolean;
}>();
</script>
