<template>
  <div class="fixed bottom-16 left-0 right-0 z-40 glass border-t border-border p-3">
    <div class="flex items-end gap-2">
      <div ref="settingsRef" class="relative">
        <button
          class="p-2.5 rounded-full bg-secondary text-muted-foreground hover:text-foreground hover:bg-primary/10 transition-colors"
          @click="settingsOpen = !settingsOpen"
        >
          <Settings2 class="w-5 h-5" />
        </button>

        <div
          v-if="settingsOpen"
          class="absolute bottom-12 left-0 w-72 p-3 rounded-lg bg-popover border border-border shadow-lg z-50"
        >
          <div class="space-y-4">
            <div class="space-y-2">
              <div class="flex items-center gap-2 text-xs text-muted-foreground">
                <Cpu class="w-3.5 h-3.5" />
                <span>引擎切换</span>
              </div>
              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="eng in engines"
                  :key="eng.id"
                  @click="onEngineChange(eng.id)"
                  :class="[
                    'px-2.5 py-1 text-xs rounded-md transition-colors',
                    engine === eng.id
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary text-muted-foreground hover:text-foreground'
                  ]"
                >
                  {{ eng.name }}
                </button>
              </div>
            </div>

            <div class="space-y-2">
              <div class="flex items-center gap-2 text-xs text-muted-foreground">
                <Brain class="w-3.5 h-3.5" />
                <span>模型切换</span>
              </div>
              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="m in models"
                  :key="m.id"
                  @click="onModelChange(m.id)"
                  :class="[
                    'px-2.5 py-1 text-xs rounded-md transition-colors',
                    model === m.id
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary text-muted-foreground hover:text-foreground'
                  ]"
                >
                  {{ m.name }}
                </button>
              </div>
            </div>

            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-xs text-muted-foreground">
                <Lightbulb class="w-3.5 h-3.5" />
                <span>思考模式</span>
              </div>
              <label class="inline-flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  class="accent-primary"
                  :checked="thinkingEnabled"
                  @change="onThinkingChange(($event.target as HTMLInputElement).checked)"
                />
              </label>
            </div>

            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-xs text-muted-foreground">
                <ListChecks class="w-3.5 h-3.5" />
                <span>Plan Mode</span>
              </div>
              <label class="inline-flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  class="accent-primary"
                  :checked="planModeEnabled"
                  @change="onPlanModeChange(($event.target as HTMLInputElement).checked)"
                />
              </label>
            </div>
          </div>
        </div>
      </div>

      <div
        class="flex-1 bg-secondary rounded-2xl border border-border focus-within:border-primary/50 transition-colors relative"
      >
        <!-- 🔥 斜杠命令提示下拉列表 -->
        <div
          v-if="showCommandSuggestions"
          ref="commandListRef"
          class="absolute bottom-full left-0 w-full mb-2 bg-popover border border-border rounded-lg shadow-lg max-h-64 overflow-y-auto z-50"
        >
          <div
            v-for="(cmd, index) in filteredCommands"
            :key="cmd.name"
            :class="[
              'px-4 py-2.5 cursor-pointer transition-colors',
              index === selectedCommandIndex
                ? 'bg-primary/10 text-primary'
                : 'hover:bg-muted/50'
            ]"
            @click="selectCommand(cmd.name)"
            @mouseenter="selectedCommandIndex = index"
            :ref="(el) => setCommandItemRef(el, index)"
          >
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium">
                <span>{{ getCommandParts(cmd.name).prefix }}</span>
                <span class="text-primary">{{ getCommandParts(cmd.name).match }}</span>
                <span>{{ getCommandParts(cmd.name).suffix }}</span>
              </span>
              <span class="text-xs text-muted-foreground">{{ cmd.description }}</span>
            </div>
          </div>
        </div>

        <textarea
          ref="textareaRef"
          v-model="input"
          @keydown.enter.exact="handleKeyDown"
          @keydown.up.prevent="handleArrowUp"
          @keydown.down.prevent="handleArrowDown"
          @keydown.escape="hideCommandSuggestions"
          @compositionstart="isComposing = true"
          @compositionend="isComposing = false"
          @input="handleInput"
          placeholder="描述你想要做的事..."
          rows="1"
          :class="[
            'w-full px-4 py-3 bg-transparent text-sm resize-none placeholder:text-muted-foreground focus:outline-none max-h-32',
            showCommandSuggestions ? 'text-primary' : ''
          ]"
          :disabled="disabled"
          :style="{ minHeight: '44px' }"
        />
      </div>

      <button
        v-if="isStreaming"
        @click="onStop"
        class="p-2.5 rounded-full bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors"
      >
        <StopCircle class="w-5 h-5" />
      </button>
      <button
        v-else
        @click="handleSubmit"
        :disabled="!input.trim() || disabled"
        class="p-2.5 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
      >
        <Send class="w-5 h-5" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, toRefs, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { Send, StopCircle, Settings2, Cpu, Brain, Lightbulb, ListChecks } from 'lucide-vue-next';
import { AIEngine, AIModel } from '@/types';

const props = defineProps<{
  onSend: (message: string) => void;
  isStreaming?: boolean;
  onStop?: () => void;
  disabled?: boolean;
  engine: AIEngine;
  model: AIModel;
  projectPath?: string;
  thinkingEnabled: boolean;
  planModeEnabled: boolean;
  onEngineChange: (engine: AIEngine) => void;
  onModelChange: (model: AIModel) => void;
  onThinkingChange: (enabled: boolean) => void;
  onPlanModeChange: (enabled: boolean) => void;
}>();

const input = ref('');
const settingsOpen = ref(false);
const settingsRef = ref<HTMLElement | null>(null);
const isComposing = ref(false); // 🔥 追踪输入法 composing 状态
const textareaRef = ref<HTMLTextAreaElement | null>(null);
const showCommandSuggestions = ref(false);
const selectedCommandIndex = ref(0);
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
const commandListRef = ref<HTMLElement | null>(null);
const commandItemRefs = ref<HTMLElement[]>([]);

// 🔥 完整的斜杠命令列表（基于 Claude CLI Skills）
interface SlashCommand {
  name: string;
  description: string;
  category: 'session' | 'context' | 'system' | 'git' | 'config' | 'custom' | 'project';
}

const builtInCommands: SlashCommand[] = [
  // Session 管理
  { name: '/clear', description: '清除会话历史', category: 'session' },
  { name: '/compact', description: '压缩会话上下文', category: 'session' },
  { name: '/resume', description: '恢复之前的会话', category: 'session' },
  { name: '/rename', description: '重命名当前会话', category: 'session' },
  { name: '/export', description: '导出会话到文件', category: 'session' },

  // 上下文和成本
  { name: '/context', description: '查看上下文使用情况', category: 'context' },
  { name: '/cost', description: '查看 Token 使用统计', category: 'context' },
  { name: '/usage', description: '查看订阅计划用量', category: 'context' },
  { name: '/stats', description: '查看使用统计和历史', category: 'context' },

  // 系统和配置
  { name: '/help', description: '显示帮助信息', category: 'system' },
  { name: '/config', description: '打开设置界面', category: 'config' },
  { name: '/status', description: '显示版本和连接状态', category: 'system' },
  { name: '/doctor', description: '检查安装健康状态', category: 'system' },
  { name: '/model', description: '选择或更换 AI 模型', category: 'config' },
  { name: '/permissions', description: '查看或更新权限', category: 'config' },

  // 项目和代码
  { name: '/init', description: '初始化项目 CLAUDE.md', category: 'system' },
  { name: '/memory', description: '编辑 CLAUDE.md 记忆文件', category: 'system' },
  { name: '/review', description: '请求代码审查', category: 'git' },
  { name: '/todos', description: '列出当前 TODO 项', category: 'system' },
  { name: '/rewind', description: '回退会话或代码', category: 'git' },

  // 工具和集成
  { name: '/mcp', description: '管理 MCP 服务器连接', category: 'system' },
  { name: '/hooks', description: '管理 Hook 配置', category: 'config' },
  { name: '/plugin', description: '管理 Claude Code 插件', category: 'system' },
  { name: '/agents', description: '管理自定义 AI 子代理', category: 'system' },
  { name: '/bashes', description: '列出后台任务', category: 'system' },
];

// 🔥 动态模型列表（从后端 API 加载）
interface DynamicModel {
  id: string;
  name: string;
  description: string;
  context_window: number;
  is_default: boolean;
}
const dynamicModels = ref<DynamicModel[]>([]);

// 🔥 动态斜杠命令（从后端 API 加载）
const dynamicCommands = ref<SlashCommand[]>([]);

// 所有可用命令（动态命令优先，回退到内置命令）
const availableCommands = computed(() => {
  if (dynamicCommands.value.length > 0) {
    return [...dynamicCommands.value];
  }
  return [...builtInCommands];
});

// 🔥 根据当前引擎加载模型列表
const loadModels = async () => {
  try {
    const engineName = props.engine;
    const response = await fetch(`${apiBaseUrl}/v1/${engineName}/models`);
    if (response.ok) {
      const models = await response.json();
      dynamicModels.value = models;
      syncModelSelection(models);
      console.log(`[ChatInput] Loaded ${engineName} models:`, models.length);
    }
  } catch (error) {
    console.warn('[ChatInput] Failed to load models:', error);
    dynamicModels.value = [];
    syncModelSelection([]);
  }
};

// 🔥 根据当前引擎加载斜杠命令
const loadSlashCommands = async () => {
  try {
    const engineName = props.engine;
    const projectPath = props.projectPath;
    const query = projectPath
      ? `?project_path=${encodeURIComponent(projectPath)}`
      : '';
    const response = await fetch(`${apiBaseUrl}/v1/${engineName}/slash-commands${query}`);
    if (response.ok) {
      const commands = await response.json();
      dynamicCommands.value = commands.map((cmd: any) => ({
        // 后端返回的 name 不带 /，需要加上前缀
        name: cmd.name.startsWith('/') ? cmd.name : `/${cmd.name}`,
        description: cmd.description,
        category: cmd.category as SlashCommand['category'],
      }));
      console.log(`[ChatInput] Loaded ${engineName} slash commands:`, dynamicCommands.value.length);
    }
  } catch (error) {
    console.warn('[ChatInput] Failed to load slash commands:', error);
    dynamicCommands.value = [];
  }
};

// 🔥 监听引擎变化，重新加载模型和命令
watch([() => props.engine, () => props.projectPath], () => {
  loadModels();
  loadSlashCommands();
}, { immediate: false });

// 组件挂载时加载所有数据
onMounted(() => {
  loadModels();
  loadSlashCommands();
  document.addEventListener('mousedown', handleDocumentClick);
});

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleDocumentClick);
});

const engines: { id: AIEngine; name: string }[] = [
  { id: 'claude', name: 'Claude Code' },
  { id: 'codex', name: 'Codex' },
  { id: 'gemini', name: 'Gemini CLI' },
];

// 按引擎分组的模型列表
const modelsByEngine: Record<AIEngine, { id: AIModel; name: string }[]> = {
  claude: [
    { id: 'claude-sonnet-4-5', name: 'Claude Sonnet 4.5' },
    { id: 'claude-sonnet-4-5-thinking', name: 'Claude Sonnet 4.5 (Thinking)' },
    { id: 'claude-opus-4-5', name: 'Claude Opus 4.5' },
    { id: 'claude-4-sonnet', name: 'Claude 4 Sonnet' },
    { id: 'claude-4-opus', name: 'Claude 4 Opus' },
  ],
  codex: [
    { id: 'gpt-5', name: 'GPT-5' },
    { id: 'gpt-5-mini', name: 'GPT-5 Mini' },
  ],
  gemini: [
    { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro' },
    { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash' },
  ],
};

const pickDefaultModel = (models: DynamicModel[]) => {
  const apiDefault = models.find(m => m.is_default)?.id || models[0]?.id;
  const fallbackDefault = modelsByEngine[props.engine]?.[0]?.id;
  return apiDefault || fallbackDefault || '';
};

const syncModelSelection = (models: DynamicModel[]) => {
  const selectedModel = props.model;
  const availableIds = new Set(models.map(m => m.id));
  if (models.length > 0 && availableIds.has(selectedModel)) {
    return;
  }
  const fallback = pickDefaultModel(models);
  if (fallback && fallback !== selectedModel) {
    props.onModelChange(fallback as AIModel);
  }
};

const handleDocumentClick = (event: MouseEvent) => {
  if (!settingsOpen.value) return;
  const target = event.target as Node | null;
  if (settingsRef.value && target && !settingsRef.value.contains(target)) {
    settingsOpen.value = false;
  }
};

/**
 * 处理输入变化，检测斜杠命令
 */
const handleInput = () => {
  const trimmed = input.value.trim();

  // 检测是否输入斜杠命令
  if (trimmed.startsWith('/')) {
    showCommandSuggestions.value = true;
    selectedCommandIndex.value = 0;
  } else {
    showCommandSuggestions.value = false;
  }
};

/**
 * 过滤匹配的命令
 */
const filteredCommands = computed(() => {
  const trimmed = input.value.trim();
  if (!trimmed.startsWith('/')) return [];

  // 提取查询部分（去掉开头的 /）
  const query = trimmed.slice(1).toLowerCase();

  // 如果只输入了 /，显示所有命令
  if (query === '') {
    return availableCommands.value;
  }

  // 按命令名匹配（命令名已包含 / 前缀）
  return availableCommands.value.filter(cmd => {
    const cmdName = cmd.name.toLowerCase().replace(/^\//, '');
    return cmdName.includes(query);
  });
});

const setCommandItemRef = (el: Element | null, index: number) => {
  if (!el) return;
  commandItemRefs.value[index] = el as HTMLElement;
};

const scrollSelectedIntoView = async () => {
  await nextTick();
  const container = commandListRef.value;
  const item = commandItemRefs.value[selectedCommandIndex.value];
  if (!container || !item) return;
  const viewTop = container.scrollTop;
  const viewBottom = viewTop + container.clientHeight;
  const itemTop = item.offsetTop;
  const itemBottom = itemTop + item.offsetHeight;
  if (itemTop < viewTop) {
    container.scrollTop = itemTop;
  } else if (itemBottom > viewBottom) {
    container.scrollTop = itemBottom - container.clientHeight;
  }
};

/**
 * 处理上箭头按键
 */
const handleArrowUp = () => {
  if (!showCommandSuggestions.value) return;

  if (selectedCommandIndex.value > 0) {
    selectedCommandIndex.value--;
  } else {
    selectedCommandIndex.value = filteredCommands.value.length - 1;
  }
  scrollSelectedIntoView();
};

/**
 * 处理下箭头按键
 */
const handleArrowDown = () => {
  if (!showCommandSuggestions.value) return;

  if (selectedCommandIndex.value < filteredCommands.value.length - 1) {
    selectedCommandIndex.value++;
  } else {
    selectedCommandIndex.value = 0;
  }
  scrollSelectedIntoView();
};

/**
 * 隐藏命令提示
 */
const hideCommandSuggestions = () => {
  showCommandSuggestions.value = false;
  selectedCommandIndex.value = 0;
};

/**
 * 选择命令
 */
const selectCommand = (commandName: string) => {
  input.value = commandName;
  hideCommandSuggestions();
  textareaRef.value?.focus();
};

watch(filteredCommands, () => {
  commandItemRefs.value = [];
  selectedCommandIndex.value = 0;
  if (showCommandSuggestions.value) {
    scrollSelectedIntoView();
  }
});

const getCommandParts = (commandName: string) => {
  const trimmed = input.value.trim();
  if (!trimmed.startsWith('/')) {
    return { prefix: commandName, match: '', suffix: '' };
  }
  const query = trimmed.slice(1).toLowerCase();
  if (!query) {
    return { prefix: commandName, match: '', suffix: '' };
  }
  const name = commandName.startsWith('/') ? commandName.slice(1) : commandName;
  const lowerName = name.toLowerCase();
  const index = lowerName.indexOf(query);
  if (index === -1) {
    return { prefix: commandName, match: '', suffix: '' };
  }
  const prefix = `/${name.slice(0, index)}`;
  const match = name.slice(index, index + query.length);
  const suffix = name.slice(index + query.length);
  return { prefix, match, suffix };
};

/**
 * 处理回车键按下
 * 🔥 关键：在输入法 composing 状态下不发送消息
 * 解决搜狗等输入法回车选字时误触发发送的问题
 */
const handleKeyDown = (event: KeyboardEvent) => {
  // 如果正在显示命令提示，回车选择命令
  if (showCommandSuggestions.value && filteredCommands.value.length > 0) {
    event.preventDefault();
    const selectedCommand = filteredCommands.value[selectedCommandIndex.value];
    if (selectedCommand) {
      selectCommand(selectedCommand.name);
    }
    return;
  }

  // 如果正在使用输入法输入（composing），不处理回车
  if (isComposing.value) {
    return;
  }

  // 阻止默认行为并发送消息
  event.preventDefault();
  handleSubmit();
};

const handleSubmit = () => {
  if (!input.value.trim() || props.disabled) return;
  hideCommandSuggestions();
  props.onSend(input.value);
  input.value = '';
};

// 🔥 根据当前引擎动态获取模型列表（优先使用 API 数据）
const models = computed(() => {
  if (dynamicModels.value.length > 0) {
    return dynamicModels.value.map(m => ({
      id: m.id as AIModel,
      name: m.name,
    }));
  }
  const fallback = modelsByEngine[props.engine] || [];
  if (fallback.length === 0) {
    console.warn(`[ChatInput] No models loaded for ${props.engine}, API may have failed`);
  }
  return fallback;
});

const {
  isStreaming,
  onStop,
  disabled,
  engine,
  model,
  thinkingEnabled,
  planModeEnabled,
  onEngineChange,
  onModelChange,
  onThinkingChange,
  onPlanModeChange,
} = toRefs(props);
</script>
