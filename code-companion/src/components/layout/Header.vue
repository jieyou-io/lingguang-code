<template>
  <header :class="['sticky top-0 z-40', { 'glass border-b border-border': !transparent }]">
    <div class="flex items-center justify-between h-14 px-4">
      <div class="flex items-center gap-3 min-w-0">
        <button
          v-if="back"
          @click="handleBack"
          class="p-1 -ml-1 text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronLeft :size="24" />
        </button>
        <div class="min-w-0">
          <h1 class="text-base font-semibold truncate">{{ title }}</h1>
          <p v-if="subtitle" class="text-xs text-muted-foreground truncate">{{ subtitle }}</p>
        </div>
      </div>
      <div v-if="$slots.actions" class="flex items-center gap-2">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { ChevronLeft } from 'lucide-vue-next';

const props = withDefaults(defineProps<{
  title: string;
  subtitle?: string;
  back?: boolean;
  transparent?: boolean;
  useRouterBack?: boolean;
}>(), {
  useRouterBack: true,
});

const emit = defineEmits<{
  back: [];
}>();

const router = useRouter();

const handleBack = () => {
  emit('back');
  if (props.useRouterBack) {
    router.back();
  }
};
</script>
