<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" @click.self="close">
    <div class="bg-background rounded-lg p-6 max-w-[600px] w-full m-4 max-h-[90vh] overflow-y-auto" @click.stop>
      <!-- Header -->
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-lg font-semibold flex items-center gap-2">
            <Plus class="w-5 h-5 text-primary" />
            新建 MCP 服务器
          </h2>
          <p class="text-sm text-muted-foreground mt-1">
            为 {{ engineName }} 添加新的 MCP 服务器
          </p>
        </div>
        <button class="text-muted-foreground hover:text-foreground text-2xl" @click="close">×</button>
      </div>

      <!-- 选项卡 -->
      <div class="flex gap-2 mb-4 border-b border-border">
        <button
          type="button"
          @click="inputMode = 'form'"
          :class="[
            'px-4 py-2 text-sm transition-colors',
            inputMode === 'form'
              ? 'border-b-2 border-primary text-primary font-medium'
              : 'text-muted-foreground hover:text-foreground'
          ]"
        >
          表单输入
        </button>
        <button
          type="button"
          @click="inputMode = 'json'"
          :class="[
            'px-4 py-2 text-sm transition-colors',
            inputMode === 'json'
              ? 'border-b-2 border-primary text-primary font-medium'
              : 'text-muted-foreground hover:text-foreground'
          ]"
        >
          JSON 导入
        </button>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <!-- JSON 输入模式 -->
        <div v-if="inputMode === 'json'" class="space-y-2">
          <label class="text-sm font-medium">JSON 配置 *</label>
          <textarea
            v-model="jsonInput"
            placeholder='{"name": "filesystem", "transport": "stdio", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]}'
            rows="10"
            class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm font-mono"
            :class="{ 'border-destructive': jsonError }"
          />
          <p v-if="jsonError" class="text-xs text-destructive">{{ jsonError }}</p>
          <p v-else class="text-xs text-muted-foreground">粘贴 MCP 服务器的 JSON 配置</p>
        </div>

        <!-- 表单输入模式 -->
        <template v-else>
        <!-- 服务器名称 -->
        <div class="space-y-2">
          <label class="text-sm font-medium">服务器名称 *</label>
          <input
            v-model="formData.name"
            type="text"
            placeholder="例如: filesystem"
            class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm"
            required
          />
        </div>

        <!-- 传输协议 -->
        <div class="space-y-2">
          <label class="text-sm font-medium">传输协议 *</label>
          <div class="flex gap-4">
            <label class="flex items-center gap-2">
              <input
                v-model="formData.transport"
                type="radio"
                value="stdio"
                class="accent-primary"
              />
              <span class="text-sm">stdio</span>
            </label>
            <label class="flex items-center gap-2">
              <input
                v-model="formData.transport"
                type="radio"
                value="sse"
                class="accent-primary"
              />
              <span class="text-sm">SSE</span>
            </label>
          </div>
        </div>

        <!-- stdio 配置 -->
        <div v-if="formData.transport === 'stdio'" class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-medium">命令 *</label>
            <input
              v-model="formData.command"
              type="text"
              placeholder="例如: npx"
              class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm"
              :required="formData.transport === 'stdio'"
            />
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium">参数</label>
            <input
              v-model="argsInput"
              type="text"
              placeholder="例如: -y @modelcontextprotocol/server-filesystem /path"
              class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm"
            />
            <p class="text-xs text-muted-foreground">多个参数用空格分隔</p>
          </div>
        </div>

        <!-- SSE 配置 -->
        <div v-if="formData.transport === 'sse'" class="space-y-2">
          <label class="text-sm font-medium">URL *</label>
          <input
            v-model="formData.url"
            type="url"
            placeholder="例如: http://localhost:3000/sse"
            class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm"
            :required="formData.transport === 'sse'"
          />
        </div>

        <!-- 环境变量 -->
        <div class="space-y-2">
          <label class="text-sm font-medium">环境变量（可选）</label>
          <textarea
            v-model="envInput"
            placeholder="KEY1=value1&#10;KEY2=value2"
            rows="3"
            class="w-full px-3 py-2 rounded-md border border-border bg-background text-sm font-mono"
          />
          <p class="text-xs text-muted-foreground">每行一个，格式: KEY=VALUE</p>
        </div>
        </template>

        <!-- 按钮 -->
        <div class="flex gap-3 pt-4">
          <button
            type="button"
            @click="close"
            class="flex-1 px-4 py-2 rounded-md border border-border hover:bg-secondary transition-colors text-sm"
          >
            取消
          </button>
          <button
            type="submit"
            :disabled="submitting"
            class="flex-1 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-sm disabled:opacity-50"
          >
            {{ submitting ? '创建中...' : '创建' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { Plus } from 'lucide-vue-next';
import { createMCPServer } from '@/lib/services/mcp';
import type { MCPEngine, MCPTransport } from '@/types/mcp';
import { useToast } from '@/composables/useToast';

const props = defineProps<{
  open: boolean;
  engine: MCPEngine;
  engineName: string;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}>();

const { toast } = useToast();
const submitting = ref(false);
const inputMode = ref<'form' | 'json'>('form');
const jsonInput = ref('');
const jsonError = ref('');

// 表单数据
const formData = ref<{
  name: string;
  transport: MCPTransport;
  command: string;
  url: string;
}>({
  name: '',
  transport: 'stdio',
  command: '',
  url: '',
});

// 辅助输入字段
const argsInput = ref('');
const envInput = ref('');

// 关闭对话框
const close = () => {
  props.onOpenChange(false);
  // 重置表单
  formData.value = {
    name: '',
    transport: 'stdio',
    command: '',
    url: '',
  };
  argsInput.value = '';
  envInput.value = '';
  inputMode.value = 'form';
  jsonInput.value = '';
  jsonError.value = '';
};

// 提交表单
const handleSubmit = async () => {
  submitting.value = true;
  jsonError.value = '';

  try {
    let requestData;

    // JSON 模式：解析 JSON
    if (inputMode.value === 'json') {
      try {
        const parsed = JSON.parse(jsonInput.value);

        // 验证必需字段
        if (!parsed.name) {
          throw new Error('缺少必需字段: name');
        }
        if (!parsed.transport) {
          throw new Error('缺少必需字段: transport');
        }
        if (parsed.transport === 'stdio' && !parsed.command) {
          throw new Error('stdio 模式需要 command 字段');
        }
        if (parsed.transport === 'sse' && !parsed.url) {
          throw new Error('sse 模式需要 url 字段');
        }

        requestData = {
          name: parsed.name,
          transport: parsed.transport,
          args: parsed.args || [],
          env: parsed.env || {},
          ...(parsed.command && { command: parsed.command }),
          ...(parsed.url && { url: parsed.url }),
        };
      } catch (error) {
        jsonError.value = error instanceof Error ? error.message : 'JSON 格式错误';
        submitting.value = false;
        return;
      }
    } else {
      // 表单模式：从表单数据构建
      // 解析参数
      const args = argsInput.value
        .trim()
        .split(/\s+/)
        .filter(arg => arg.length > 0);

      // 解析环境变量
      const env: Record<string, string> = {};
      if (envInput.value.trim()) {
        envInput.value.split('\n').forEach(line => {
          const [key, ...valueParts] = line.split('=');
          if (key && valueParts.length > 0) {
            env[key.trim()] = valueParts.join('=').trim();
          }
        });
      }

      requestData = {
        name: formData.value.name,
        transport: formData.value.transport,
        args,
        env,
        ...(formData.value.transport === 'stdio' && { command: formData.value.command }),
        ...(formData.value.transport === 'sse' && { url: formData.value.url }),
      };
    }

    // 调用 API 创建服务器
    await createMCPServer(props.engine, requestData);

    toast({
      title: '创建成功',
      description: `MCP 服务器 ${formData.value.name} 已创建`,
    });

    close();
    props.onSuccess();
  } catch (error) {
    toast({
      title: '创建失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    });
  } finally {
    submitting.value = false;
  }
};
</script>
