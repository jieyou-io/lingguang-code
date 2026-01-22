<template>
  <div class="my-2 p-4 rounded-lg border border-amber-500/30 bg-amber-500/10">
    <div class="flex items-start gap-3">
      <div class="flex-shrink-0 w-8 h-8 rounded-full bg-amber-500/20 flex items-center justify-center">
        <ShieldAlert class="w-4 h-4 text-amber-500" />
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1">
          <span class="font-medium text-amber-500">权限请求</span>
          <span class="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-500">
            {{ toolName }}
          </span>
        </div>
        <p class="text-sm text-muted-foreground mb-3">
          {{ description }}
        </p>

        <!-- 文件路径预览 -->
        <div v-if="filePath" class="mb-3 p-2 rounded bg-secondary/50 font-mono text-xs text-muted-foreground overflow-x-auto">
          {{ filePath }}
        </div>

        <!-- 操作按钮 -->
        <div v-if="!responded" class="flex items-center gap-2">
          <button
            @click="handleAllow"
            :disabled="loading"
            class="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-green-500 text-white hover:bg-green-600 disabled:opacity-50 transition-colors"
          >
            <Check class="w-3.5 h-3.5" />
            允许
          </button>
          <button
            @click="handleDeny"
            :disabled="loading"
            class="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-red-500 text-white hover:bg-red-600 disabled:opacity-50 transition-colors"
          >
            <X class="w-3.5 h-3.5" />
            拒绝
          </button>
          <span v-if="loading" class="text-xs text-muted-foreground ml-2">
            处理中...
          </span>
        </div>

        <!-- 已响应状态 -->
        <div v-else class="flex items-center gap-2">
          <span
            :class="[
              'flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg',
              response === 'y' ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'
            ]"
          >
            <Check v-if="response === 'y'" class="w-3.5 h-3.5" />
            <X v-else class="w-3.5 h-3.5" />
            {{ response === 'y' ? '已允许' : '已拒绝' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { ShieldAlert, Check, X } from 'lucide-vue-next';

const props = defineProps<{
  toolName: string;
  toolId: string;
  sessionId: string;
  input?: any;
}>();

const emit = defineEmits<{
  respond: [response: 'y' | 'n'];
}>();

const loading = ref(false);
const responded = ref(false);
const response = ref<'y' | 'n' | null>(null);

const description = computed(() => {
  const descriptions: Record<string, string> = {
    Write: '请求写入文件',
    Edit: '请求编辑文件',
    Bash: '请求执行命令',
    NotebookEdit: '请求编辑 Notebook',
    KillShell: '请求终止进程',
  };
  return descriptions[props.toolName] || `请求使用 ${props.toolName} 工具`;
});

const filePath = computed(() => {
  if (!props.input) return null;
  return props.input.file_path || props.input.filePath || props.input.path || props.input.command;
});

const handleAllow = async () => {
  loading.value = true;
  try {
    await sendPermissionResponse('y');
    response.value = 'y';
    responded.value = true;
    emit('respond', 'y');
  } catch (error) {
    console.error('Failed to send permission response:', error);
  } finally {
    loading.value = false;
  }
};

const handleDeny = async () => {
  loading.value = true;
  try {
    await sendPermissionResponse('n');
    response.value = 'n';
    responded.value = true;
    emit('respond', 'n');
  } catch (error) {
    console.error('Failed to send permission response:', error);
  } finally {
    loading.value = false;
  }
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

const sendPermissionResponse = async (resp: 'y' | 'n') => {
  const res = await fetch(`${API_BASE_URL}/v1/claude/permission`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sessionId: props.sessionId,
      response: resp,
    }),
  });
  if (!res.ok) {
    throw new Error(`Permission response failed: ${res.status}`);
  }
};
</script>
