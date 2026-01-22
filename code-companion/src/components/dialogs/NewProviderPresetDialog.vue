<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" @click.self="close">
    <div class="bg-background rounded-lg p-6 max-w-md w-full m-4 max-h-[90vh] overflow-y-auto" @click.stop>
      <!-- Header -->
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold">添加代理商预设</h2>
        <button class="text-muted-foreground hover:text-foreground text-2xl" @click="close">×</button>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <!-- 预设 ID -->
        <div class="space-y-2">
          <label class="text-sm font-medium">预设 ID *</label>
          <input
            v-model="formData.id"
            type="text"
            class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="例如: my-provider"
            required
          />
        </div>

        <!-- 预设名称 -->
        <div class="space-y-2">
          <label class="text-sm font-medium">预设名称 *</label>
          <input
            v-model="formData.name"
            type="text"
            class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="例如: My Provider"
            required
          />
        </div>

        <!-- 描述 -->
        <div class="space-y-2">
          <label class="text-sm font-medium">描述（可选）</label>
          <textarea
            v-model="formData.description"
            rows="2"
            class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary resize-none"
            placeholder="简要描述这个代理商"
          />
        </div>

        <!-- API Key -->
        <div class="space-y-2">
          <label class="text-sm font-medium">API Key *</label>
          <input
            v-model="formData.apiKey"
            type="password"
            class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="输入 API Key"
            required
          />
        </div>

        <!-- Base URL -->
        <div class="space-y-2">
          <label class="text-sm font-medium">Base URL *</label>
          <input
            v-model="formData.baseUrl"
            type="text"
            class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="例如: https://api.example.com"
            required
          />
        </div>

        <!-- 模型 -->
        <div class="space-y-2">
          <label class="text-sm font-medium">模型（可选）</label>
          <input
            v-model="formData.model"
            type="text"
            class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="例如: gpt-5-codex"
          />
        </div>

        <!-- 错误提示 -->
        <div v-if="error" class="p-3 text-sm text-red-500 bg-red-50 dark:bg-red-900/20 rounded-lg">
          {{ error }}
        </div>

        <!-- 操作按钮 -->
        <div class="flex gap-2 justify-end">
          <button
            type="button"
            class="px-4 py-2 text-sm border border-border rounded-lg hover:bg-secondary transition-colors"
            @click="close"
          >
            取消
          </button>
          <button
            type="submit"
            class="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
            :disabled="!isValid || submitting"
          >
            {{ submitting ? '添加中...' : '添加' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

interface Props {
  open: boolean;
  engine: 'claude' | 'codex' | 'gemini';
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'submit', data: any): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const formData = ref({
  id: '',
  name: '',
  description: '',
  apiKey: '',
  baseUrl: '',
  model: '',
});

const error = ref('');
const submitting = ref(false);

const isValid = computed(() => {
  return formData.value.id && formData.value.name && formData.value.apiKey && formData.value.baseUrl;
});

const close = () => {
  emit('update:open', false);
};

const handleSubmit = async () => {
  if (!isValid.value) {
    error.value = '请填写所有必填字段';
    return;
  }

  submitting.value = true;
  error.value = '';

  try {
    // 根据引擎类型构建配置
    let config: any = {};

    if (props.engine === 'claude') {
      config = {
        env: {
          ANTHROPIC_BASE_URL: formData.value.baseUrl,
          ANTHROPIC_API_KEY: formData.value.apiKey,
        },
      };
      if (formData.value.model) {
        config.env.ANTHROPIC_MODEL = formData.value.model;
      }
    } else if (props.engine === 'codex') {
      config = {
        auth: {
          OPENAI_API_KEY: formData.value.apiKey,
        },
        config: `model_provider = "custom"
model = "${formData.value.model || 'gpt-5-codex'}"
model_reasoning_effort = "high"
disable_response_storage = true

[model_providers.custom]
name = "custom"
base_url = "${formData.value.baseUrl}"
wire_api = "responses"
requires_openai_auth = true`,
      };
    } else if (props.engine === 'gemini') {
      config = {
        env: {
          GOOGLE_GEMINI_BASE_URL: formData.value.baseUrl,
          GEMINI_API_KEY: formData.value.apiKey,
        },
      };
      if (formData.value.model) {
        config.env.GEMINI_MODEL = formData.value.model;
      }
    }

    const presetData = {
      id: formData.value.id,
      name: formData.value.name,
      description: formData.value.description || undefined,
      config,
    };

    emit('submit', presetData);
    emit('update:open', false);

    // 重置表单
    formData.value = {
      id: '',
      name: '',
      description: '',
      apiKey: '',
      baseUrl: '',
      model: '',
    };
  } catch (err) {
    error.value = err instanceof Error ? err.message : '添加失败';
  } finally {
    submitting.value = false;
  }
};
</script>
