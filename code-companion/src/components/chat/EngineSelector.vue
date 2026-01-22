<template>
  <div class="relative inline-block">
    <button
      class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary/50 border border-border hover:bg-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      :disabled="disabled"
      @click="toggle"
    >
      <EngineIcon :engine="engine" size="sm" />
      <span class="text-xs font-medium">{{ currentEngine.name }}</span>
      <ChevronDown class="w-3 h-3 text-muted-foreground" />
    </button>

    <div
      v-if="open"
      class="absolute left-0 mt-2 w-56 rounded-lg border border-border bg-popover shadow-lg z-50"
    >
      <button
        v-for="eng in engines"
        :key="eng.id"
        class="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-muted transition-colors"
        @click="selectEngine(eng.id)"
      >
        <EngineIcon :engine="eng.id" size="md" />
        <div class="flex-1">
          <p class="text-sm font-medium">{{ eng.name }}</p>
          <p class="text-xs text-muted-foreground">{{ eng.description }}</p>
        </div>
        <Check v-if="engine === eng.id" class="w-4 h-4 text-primary" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { Check, ChevronDown } from 'lucide-vue-next';
import { AIEngine } from '@/types';
import EngineIcon from '@/components/icons/EngineIcon.vue';

const props = defineProps<{
  engine: AIEngine;
  onChange: (engine: AIEngine) => void;
  disabled?: boolean;
}>();

const open = ref(false);

const engines: { id: AIEngine; name: string; description: string }[] = [
  { id: 'claude', name: 'Claude', description: 'Anthropic 的对话模型' },
  { id: 'codex', name: 'Codex', description: 'OpenAI 代码专家' },
  { id: 'gemini', name: 'Gemini', description: 'Google 多模态模型' },
];

const currentEngine = computed(() => engines.find(e => e.id === props.engine) || engines[0]);

const toggle = () => {
  if (props.disabled) return;
  open.value = !open.value;
};

const selectEngine = (engine: AIEngine) => {
  props.onChange(engine);
  open.value = false;
};
</script>
