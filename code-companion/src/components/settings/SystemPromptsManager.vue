<template>
  <div class="space-y-4">
    <!-- 引擎选择标签 -->
    <div class="flex gap-2 border-b border-border">
      <button
        v-for="engine in engines"
        :key="engine.id"
        class="px-4 py-2 text-sm font-medium transition-colors relative"
        :class="activeEngine === engine.id
          ? 'text-primary'
          : 'text-muted-foreground hover:text-foreground'"
        @click="handleEngineChange(engine.id)"
      >
        {{ engine.label }}
        <div
          v-if="activeEngine === engine.id"
          class="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
        />
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="p-8 text-center text-muted-foreground">
      <p class="text-sm">加载中...</p>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="p-4 rounded-lg bg-destructive/10 text-destructive text-sm">
      加载失败: {{ error }}
    </div>

    <!-- 提示词编辑器 -->
    <div v-else class="space-y-3">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-sm font-medium">{{ currentEngineLabel }} 系统提示词</h3>
          <p class="text-xs text-muted-foreground mt-1">
            文件路径: {{ promptData?.file_path || '未创建' }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="hasChanges"
            class="px-3 py-1.5 text-xs rounded-lg border border-border hover:bg-secondary transition-colors"
            @click="handleReset"
          >
            重置
          </button>
          <button
            class="px-3 py-1.5 text-xs rounded-lg transition-colors"
            :class="hasChanges
              ? 'bg-primary text-primary-foreground hover:bg-primary/90'
              : 'bg-secondary text-muted-foreground cursor-not-allowed'"
            :disabled="!hasChanges || saving"
            @click="handleSave"
          >
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>

      <!-- 文本编辑器 -->
      <textarea
        v-model="editedContent"
        class="w-full h-96 p-3 text-sm font-mono rounded-lg border border-border bg-card focus:outline-none focus:ring-2 focus:ring-primary resize-none"
        placeholder="在此输入系统提示词..."
      />

      <!-- 提示信息 -->
      <div class="flex items-start gap-2 p-3 rounded-lg bg-secondary/50 text-xs text-muted-foreground">
        <div class="mt-0.5">ℹ️</div>
        <div>
          <p class="font-medium mb-1">提示词说明</p>
          <ul class="space-y-1 list-disc list-inside">
            <li>系统提示词会在每次对话开始时自动添加</li>
            <li>支持 Markdown 格式</li>
            <li>修改后需要重新开始对话才能生效</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { getSystemPrompt, updateSystemPrompt, type SystemPromptResponse } from '@/lib/system-prompts-api';
import { useToast } from '@/composables/useToast';

const { toast } = useToast();

// 引擎配置
const engines = [
  { id: 'claude', label: 'Claude' },
  { id: 'codex', label: 'Codex' },
  { id: 'gemini', label: 'Gemini' },
] as const;

type EngineId = typeof engines[number]['id'];

// 状态
const activeEngine = ref<EngineId>('claude');
const loading = ref(false);
const saving = ref(false);
const error = ref<string | null>(null);
const promptData = ref<SystemPromptResponse | null>(null);
const editedContent = ref('');
const originalContent = ref('');

// 计算属性
const currentEngineLabel = computed(() => {
  return engines.find(e => e.id === activeEngine.value)?.label || '';
});

const hasChanges = computed(() => {
  return editedContent.value !== originalContent.value;
});

// 加载提示词
const loadPrompt = async () => {
  loading.value = true;
  error.value = null;

  try {
    const data = await getSystemPrompt(activeEngine.value);
    promptData.value = data;
    editedContent.value = data.content;
    originalContent.value = data.content;
  } catch (err) {
    console.error('Failed to load system prompt:', err);
    error.value = err instanceof Error ? err.message : '加载失败';
  } finally {
    loading.value = false;
  }
};

// 保存提示词
const handleSave = async () => {
  if (!hasChanges.value || saving.value) return;

  saving.value = true;

  try {
    const data = await updateSystemPrompt(activeEngine.value, editedContent.value);
    promptData.value = data;
    originalContent.value = editedContent.value;

    toast({
      title: '保存成功',
      description: `${currentEngineLabel.value} 系统提示词已更新`,
    });
  } catch (err) {
    console.error('Failed to save system prompt:', err);
    toast({
      title: '保存失败',
      description: err instanceof Error ? err.message : '未知错误',
      variant: 'destructive',
    });
  } finally {
    saving.value = false;
  }
};

// 重置修改
const handleReset = () => {
  editedContent.value = originalContent.value;
};

// 切换引擎
const handleEngineChange = (engineId: EngineId) => {
  if (hasChanges.value) {
    const confirmed = confirm('当前有未保存的修改，切换引擎将丢失修改。是否继续？');
    if (!confirmed) return;
  }

  activeEngine.value = engineId;
  loadPrompt();
};

// 监听引擎变化
watch(activeEngine, () => {
  loadPrompt();
}, { immediate: true });
</script>
