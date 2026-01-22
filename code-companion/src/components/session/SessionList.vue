<template>
  <div class="space-y-2">
    <SessionCard
      v-for="session in sessions"
      :key="session.id"
      :session="session"
      @click="$emit('click', session)"
      @delete="$emit('delete', session.id)"
      @view-code="$emit('view-code')"
    />
  </div>
</template>

<script setup lang="ts">
import { Session } from '@/types';
import SessionCard from './SessionCard.vue';

defineProps<{
  sessions: Session[];
}>();

defineEmits<{
  click: [session: Session];
  delete: [sessionId: string];
  'view-code': [];
}>();
</script>
