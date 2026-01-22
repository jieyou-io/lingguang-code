<template>
  <AppShell>
    <Header
      :title="headerTitle"
      :back="currentView !== 'main'"
      :use-router-back="false"
      @back="handleBack"
    >
      <template #actions>
        <button
          v-if="showAddButton"
          class="p-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          @click="handleAddAction"
        >
          <Plus class="w-5 h-5" />
        </button>
      </template>
    </Header>

    <div class="p-4">
      <div v-if="currentView === 'main'" class="space-y-6">
        <section v-for="section in mainSections" :key="section.title">
          <h2 class="text-xs font-medium text-muted-foreground mb-2 px-1">{{ section.title }}</h2>
          <div class="rounded-lg bg-card border border-border overflow-hidden">
            <button
              v-for="(item, index) in section.items"
              :key="item.label"
              class="w-full flex items-center gap-3 p-4 hover:bg-secondary/50 transition-colors"
              :class="index > 0 ? 'border-t border-border' : ''"
              @click="handleItemClick(item)"
            >
              <div class="w-9 h-9 rounded-lg bg-secondary flex items-center justify-center">
                <component :is="item.icon" class="w-4 h-4 text-muted-foreground" />
              </div>
              <div class="flex-1 text-left">
                <p class="text-sm font-medium">{{ item.label }}</p>
                <p class="text-xs text-muted-foreground">{{ item.description }}</p>
              </div>
              <ChevronRight class="w-4 h-4 text-muted-foreground" />
            </button>
          </div>
        </section>

        <div class="text-center pt-4">
          <p class="text-xs text-muted-foreground">Any Code Mobile v0.1.0</p>
        </div>
      </div>

      <div v-else-if="currentView === 'plugins'" class="p-4 space-y-2">
        <div v-if="loadingPlugins" class="p-8 text-center text-muted-foreground">
          <p class="text-sm">加载中...</p>
        </div>
        <div v-else-if="plugins.length === 0" class="p-8 text-center text-muted-foreground">
          <Puzzle class="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p class="text-sm">暂无插件</p>
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="plugin in plugins"
            :key="plugin.id"
            class="rounded-lg border border-border bg-card p-4 cursor-pointer hover:bg-secondary/50 transition-colors"
            @click="handleViewPluginDetail(plugin)"
          >
            <div class="flex items-start gap-3">
              <div class="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center flex-shrink-0">
                <Puzzle class="w-5 h-5 text-muted-foreground" />
              </div>
              <div class="flex-1 min-w-0">
                <h3 class="text-sm font-medium">{{ plugin.id }}</h3>
                <p class="text-xs text-muted-foreground mt-1">
                  路径: {{ plugin.path }}
                </p>
              </div>
              <button
                class="px-3 py-1.5 text-xs rounded-lg transition-colors"
                :class="plugin.enabled
                  ? 'bg-secondary text-muted-foreground'
                  : 'bg-primary text-primary-foreground hover:bg-primary/90'"
                @click.stop="handleTogglePlugin(plugin.id, !plugin.enabled)"
              >
                {{ plugin.enabled ? '已启用' : '启用' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="currentView === 'subagents'" class="p-4 space-y-2">
        <div v-if="loadingAgents" class="p-8 text-center text-muted-foreground">
          <p class="text-sm">加载中...</p>
        </div>
        <div v-else-if="agents.length === 0" class="p-8 text-center text-muted-foreground">
          <Bot class="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p class="text-sm">暂无子代理</p>
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="agent in agents"
            :key="agent.id"
            class="rounded-lg border border-border bg-card p-4 cursor-pointer hover:bg-secondary/50 transition-colors"
            @click="handleViewAgentDetail(agent)"
          >
            <div class="flex items-start gap-3">
              <div class="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center flex-shrink-0">
                <Bot class="w-5 h-5 text-muted-foreground" />
              </div>
              <div class="flex-1 min-w-0">
                <h3 class="text-sm font-medium">{{ agent.metadata.name || agent.id }}</h3>
                <p v-if="agent.metadata.description" class="text-xs text-muted-foreground mt-1">
                  {{ agent.metadata.description }}
                </p>
              </div>
              <button
                class="px-3 py-1.5 text-xs rounded-lg transition-colors"
                :class="agent.enabled
                  ? 'bg-secondary text-muted-foreground'
                  : 'bg-primary text-primary-foreground hover:bg-primary/90'"
                @click.stop="handleToggleAgent(agent.id, !agent.enabled)"
              >
                {{ agent.enabled ? '已启用' : '启用' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="currentView === 'skills'" class="p-4 space-y-2">
        <div v-if="loadingSkills" class="p-8 text-center text-muted-foreground">
          <p class="text-sm">加载中...</p>
        </div>
        <div v-else-if="skills.length === 0" class="p-8 text-center text-muted-foreground">
          <Sparkles class="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p class="text-sm">暂无技能</p>
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="skill in skills"
            :key="skill.id"
            class="rounded-lg border border-border bg-card p-4 cursor-pointer hover:bg-secondary/50 transition-colors"
            @click="handleViewSkillDetail(skill)"
          >
            <div class="flex items-start gap-3">
              <div class="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center flex-shrink-0">
                <Sparkles class="w-5 h-5 text-muted-foreground" />
              </div>
              <div class="flex-1 min-w-0">
                <h3 class="text-sm font-medium">{{ skill.metadata.description || skill.id }}</h3>
                <p class="text-xs text-muted-foreground mt-1">
                  ID: {{ skill.id }}
                </p>
              </div>
              <button
                class="px-3 py-1.5 text-xs rounded-lg transition-colors"
                :class="skill.enabled
                  ? 'bg-secondary text-muted-foreground'
                  : 'bg-primary text-primary-foreground hover:bg-primary/90'"
                @click.stop="handleToggleSkill(skill.id, !skill.enabled)"
              >
                {{ skill.enabled ? '已启用' : '启用' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 系统提示词管理视图 -->
      <div v-else-if="currentView === 'system-prompts'" class="p-4">
        <SystemPromptsManager />
      </div>

      <div v-else-if="currentView === 'engines'" class="p-4 space-y-4">
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="engine in engineTabs"
            :key="engine.id"
            class="px-3 py-2 text-xs rounded-lg border transition-colors"
            :class="activeEngineTab === engine.id ? 'bg-primary text-primary-foreground border-primary' : 'bg-card border-border text-muted-foreground hover:text-foreground'"
            @click="activeEngineTab = engine.id"
          >
            {{ engine.label }}
          </button>
        </div>

        <!-- 代理商列表 -->
        <div class="space-y-2">
          <div v-if="loadingPresets" class="p-8 text-center text-muted-foreground">
            <p class="text-sm">加载中...</p>
          </div>
          <div v-else-if="providerPresets.length === 0" class="p-8 text-center text-muted-foreground">
            <p class="text-sm">暂无代理商配置</p>
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="preset in providerPresets"
              :key="preset.id"
              class="rounded-lg border border-border bg-card p-4 transition-colors"
              :class="isCurrentPreset(preset) ? 'border-primary/50 bg-primary/5' : ''"
            >
              <div class="flex items-start gap-3">
                <!-- 图标 -->
                <div class="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center flex-shrink-0">
                  <span class="text-lg">{{ getProviderIcon(preset) }}</span>
                </div>

                <!-- 信息 -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-1">
                    <h3 class="text-sm font-medium">{{ preset.name }}</h3>
                    <span v-if="preset.isOfficial" class="px-1.5 py-0.5 text-xs bg-blue-500/10 text-blue-500 rounded">
                      官方
                    </span>
                  </div>
                  <p v-if="preset.description" class="text-xs text-muted-foreground mb-2">
                    {{ preset.description }}
                  </p>
                  <p v-if="getProviderUrl(preset)" class="text-xs text-blue-500 truncate">
                    {{ getProviderUrl(preset) }}
                  </p>
                </div>

                <!-- 操作按钮 -->
                <div class="flex items-center gap-2 flex-shrink-0">
                  <button
                    class="px-3 py-1.5 text-xs rounded-lg transition-colors"
                    :class="isCurrentPreset(preset)
                      ? 'bg-secondary text-muted-foreground cursor-not-allowed'
                      : 'bg-primary text-primary-foreground hover:bg-primary/90'"
                    :disabled="isCurrentPreset(preset) || switching === preset.id"
                    @click="handleSwitchPreset(preset.id)"
                  >
                    {{ switching === preset.id ? '切换中...' : (isCurrentPreset(preset) ? '已启用' : '启用') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 添加按钮 -->
        <button
          class="w-full py-3 text-sm border-2 border-dashed border-border rounded-lg hover:border-primary hover:text-primary transition-colors"
          @click="handleAddPreset"
        >
          + 添加自定义代理商
        </button>
      </div>
    </div>

    <!-- 新增代理商预设对话框 -->
    <NewProviderPresetDialog
      v-model:open="showNewPresetDialog"
      :engine="currentEngineName"
      @submit="handleCreatePreset"
    />

    <!-- 详情查看对话框 -->
    <SettingsItemDetailDialog
      v-model:open="showDetailDialog"
      :item="selectedItem"
      :item-type="selectedItemType"
    />
  </AppShell>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue';
import {
  ChevronRight,
  Bell,
  Zap,
  Puzzle,
  Bot,
  Sparkles,
  Plus,
  RefreshCw,
  FileText,
} from 'lucide-vue-next';
import AppShell from '@/components/layout/AppShell.vue';
import Header from '@/components/layout/Header.vue';
import NewProviderPresetDialog from '@/components/dialogs/NewProviderPresetDialog.vue';
import SettingsItemDetailDialog from '@/components/dialogs/SettingsItemDetailDialog.vue';
import SystemPromptsManager from '@/components/settings/SystemPromptsManager.vue';
import { useToast } from '@/composables/useToast';
import { getProviderConfig, getProviderPresets, switchProvider, createProviderPreset } from '@/lib/services/providers';
import type { ProviderConfigResponse, ProviderPresetResponse, ProviderPresetCreateRequest } from '@/types/providers';
import {
  listPlugins,
  enablePlugin,
  disablePlugin,
  listAgents,
  enableAgent,
  disableAgent,
  listSkills,
  enableSkill,
  disableSkill,
  type Plugin,
  type Agent,
  type Skill,
} from '@/lib/settings-api';

interface SettingItem {
  icon: any;
  label: string;
  description: string;
  action?: string;
}

interface SettingSection {
  title: string;
  items: SettingItem[];
}

type ViewType = 'main' | 'engines' | 'plugins' | 'subagents' | 'skills' | 'system-prompts';

const { toast } = useToast();
const currentView = ref<ViewType>('main');
const activeEngineTab = ref<'claude-code' | 'codex' | 'gemini-cli'>('claude-code');

const mainSections: SettingSection[] = [
  {
    title: '通用',
    items: [{ icon: Bell, label: '通知', description: '推送与提醒设置' }],
  },
  {
    title: 'AI 引擎',
    items: [
      { icon: Zap, label: '引擎配置', description: 'Claude Code / Codex / Gemini CLI', action: 'engines' },
      { icon: FileText, label: '系统提示词', description: '管理 Claude / Codex / Gemini 提示词', action: 'system-prompts' },
    ],
  },
  {
    title: '扩展 (Claude Code)',
    items: [
      { icon: Puzzle, label: '插件', description: '管理 MCP 插件', action: 'plugins' },
      { icon: Bot, label: '子代理', description: '配置子代理', action: 'subagents' },
      { icon: Sparkles, label: '技能', description: '管理技能扩展', action: 'skills' },
    ],
  },
];

const engineTabs = [
  { id: 'claude-code', label: 'Claude Code' },
  { id: 'codex', label: 'Codex' },
  { id: 'gemini-cli', label: 'Gemini CLI' },
] as const;

// 引擎配置状态
const currentConfig = ref<ProviderConfigResponse | null>(null);
const providerPresets = ref<ProviderPresetResponse[]>([]);
const loadingPresets = ref(false);
const showNewPresetDialog = ref(false);
const switching = ref<string | null>(null);

// Plugins 状态
const plugins = ref<Plugin[]>([]);
const loadingPlugins = ref(false);

// Agents 状态
const agents = ref<Agent[]>([]);
const loadingAgents = ref(false);

// Skills 状态
const skills = ref<Skill[]>([]);
const loadingSkills = ref(false);

// 详情对话框状态
const showDetailDialog = ref(false);
const selectedItem = ref<Plugin | Agent | Skill | null>(null);
const selectedItemType = ref<'plugin' | 'agent' | 'skill'>('plugin');

// 当前引擎标签
const activeEngineLabel = computed(() => {
  return activeEngineTab.value === 'claude-code' ? 'Claude Code' :
         activeEngineTab.value === 'codex' ? 'Codex' : 'Gemini CLI';
});

// 当前引擎名称（用于 API 调用）
const currentEngineName = computed(() => {
  return activeEngineTab.value === 'claude-code' ? 'claude' :
         activeEngineTab.value === 'gemini-cli' ? 'gemini' : activeEngineTab.value;
});

// 获取代理商图标
const getProviderIcon = (preset: ProviderPresetResponse) => {
  const name = preset.name.toLowerCase();
  if (name.includes('openai') || name.includes('official')) return '🤖';
  if (name.includes('azure')) return '☁️';
  if (name.includes('anthropic') || name.includes('claude')) return 'AI';
  if (name.includes('google') || name.includes('gemini')) return '🔵';
  return preset.name.charAt(0).toUpperCase();
};

// 获取代理商 URL
const getProviderUrl = (preset: ProviderPresetResponse) => {
  const config = preset.config as any;

  if (currentEngineName.value === 'claude') {
    const env = config.env || {};
    return env.ANTHROPIC_BASE_URL || 'https://api.anthropic.com';
  }

  if (currentEngineName.value === 'codex') {
    const configData = config.config || '';
    if (typeof configData === 'string') {
      const match = configData.match(/base_url\s*=\s*"([^"]+)"/);
      return match ? match[1] : '';
    }
    return '';
  }

  if (currentEngineName.value === 'gemini') {
    const env = config.env || {};
    return env.GOOGLE_GEMINI_BASE_URL || 'https://generativelanguage.googleapis.com';
  }

  return '';
};

// 当前配置显示
const currentConfigDisplay = computed(() => {
  if (!currentConfig.value) {
    return {
      baseUrl: '未配置',
      model: '未配置',
      apiKey: '未配置',
    };
  }

  const config = currentConfig.value.config as any;

  // Claude
  if (currentEngineName.value === 'claude') {
    const env = config.env || {};
    return {
      baseUrl: env.ANTHROPIC_BASE_URL || '默认',
      model: env.ANTHROPIC_MODEL || '默认',
      apiKey: env.ANTHROPIC_API_KEY ? '••••••••' : '未配置',
    };
  }

  // Codex
  if (currentEngineName.value === 'codex') {
    const auth = config.auth || {};
    const configData = config.config || {};
    return {
      baseUrl: configData.base_url || '默认',
      model: configData.model || '默认',
      apiKey: auth.OPENAI_API_KEY ? '••••••••' : '未配置',
    };
  }

  // Gemini
  if (currentEngineName.value === 'gemini') {
    const env = config.env || {};
    return {
      baseUrl: env.GOOGLE_GEMINI_BASE_URL || '默认',
      model: env.GEMINI_MODEL || '默认',
      apiKey: env.GEMINI_API_KEY ? '••••••••' : '未配置',
    };
  }

  return {
    baseUrl: '未配置',
    model: '未配置',
    apiKey: '未配置',
  };
});

// 加载当前配置
const loadCurrentConfig = async () => {
  try {
    console.log('Loading config for engine:', currentEngineName.value);
    const config = await getProviderConfig(currentEngineName.value);
    console.log('Loaded config:', config);
    currentConfig.value = config;
  } catch (error) {
    console.error('Failed to load config:', error);
    toast({
      title: '加载配置失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    });
  }
};

// 加载代理商预设列表
const loadProviderPresets = async () => {
  loadingPresets.value = true;
  try {
    console.log('Loading presets for engine:', currentEngineName.value);

    // 获取用户保存的预设
    const userPresets = await getProviderPresets(currentEngineName.value);
    console.log('Loaded user presets:', userPresets);

    // 获取内置预设
    const builtinPresets = getBuiltinPresets(currentEngineName.value);

    // 合并内置预设和用户预设（内置预设在前）
    providerPresets.value = [...builtinPresets, ...userPresets];
  } catch (error) {
    console.error('Failed to load presets:', error);
    toast({
      title: '加载预设失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    });
  } finally {
    loadingPresets.value = false;
  }
};

// 获取内置预设
const getBuiltinPresets = (engine: string): ProviderPresetResponse[] => {
  if (engine === 'codex') {
    return [
      {
        id: 'openai-official',
        name: 'OpenAI Official',
        description: 'OpenAI 官方 Codex 服务',
        config: {
          auth: {},
          config: '',
        },
      },
      {
        id: 'azure-openai',
        name: 'Azure OpenAI',
        description: 'Microsoft Azure OpenAI 服务',
        config: {
          auth: { OPENAI_API_KEY: '' },
          config: `model_provider = "azure_openai"
model = "gpt-5-codex"
model_reasoning_effort = "high"
disable_response_storage = true

[model_providers.azure_openai]
name = "azure_openai"
base_url = "https://YOUR_RESOURCE_NAME.openai.azure.com"
wire_api = "responses"
requires_openai_auth = true`,
        },
      },
    ];
  }

  if (engine === 'claude') {
    return [
      {
        id: 'anthropic-official',
        name: 'Anthropic Official',
        description: 'Anthropic 官方 Claude 服务',
        config: {
          env: {},
        },
      },
    ];
  }

  if (engine === 'gemini') {
    return [
      {
        id: 'google-official',
        name: 'Google Official',
        description: 'Google 官方 Gemini 服务',
        config: {
          env: {},
        },
      },
    ];
  }

  return [];
};

// 判断是否为当前使用的预设
const isCurrentPreset = (preset: ProviderPresetResponse) => {
  if (!currentConfig.value) return false;

  const config = currentConfig.value.config as any;
  const presetConfig = preset.config as any;

  // Claude: 比较 env.ANTHROPIC_BASE_URL 和 env.ANTHROPIC_API_KEY
  if (currentEngineName.value === 'claude') {
    const currentEnv = config.env || {};
    const presetEnv = presetConfig.env || {};

    // 如果都没有配置 base_url，认为是官方
    if (!currentEnv.ANTHROPIC_BASE_URL && !presetEnv.ANTHROPIC_BASE_URL) {
      return preset.id === 'anthropic-official' || preset.name === 'Anthropic Official';
    }

    return currentEnv.ANTHROPIC_BASE_URL === presetEnv.ANTHROPIC_BASE_URL;
  }

  // Codex: 比较 config.base_url
  if (currentEngineName.value === 'codex') {
    const currentConfigData = config.config || {};
    const presetConfigData = presetConfig.config || '';

    // 提取 base_url
    const currentBaseUrl = currentConfigData.base_url || '';
    const presetBaseUrlMatch = typeof presetConfigData === 'string'
      ? presetConfigData.match(/base_url\s*=\s*"([^"]+)"/)
      : null;
    const presetBaseUrl = presetBaseUrlMatch ? presetBaseUrlMatch[1] : '';

    // 如果都没有配置 base_url，认为是官方
    if (!currentBaseUrl && !presetBaseUrl) {
      return preset.id === 'openai-official' || preset.name === 'OpenAI Official';
    }

    return currentBaseUrl === presetBaseUrl;
  }

  // Gemini: 比较 env.GOOGLE_GEMINI_BASE_URL
  if (currentEngineName.value === 'gemini') {
    const currentEnv = config.env || {};
    const presetEnv = presetConfig.env || {};

    // 如果都没有配置 base_url，认为是官方
    if (!currentEnv.GOOGLE_GEMINI_BASE_URL && !presetEnv.GOOGLE_GEMINI_BASE_URL) {
      return preset.id === 'google-official' || preset.name === 'Google Official';
    }

    return currentEnv.GOOGLE_GEMINI_BASE_URL === presetEnv.GOOGLE_GEMINI_BASE_URL;
  }

  return false;
};

// 切换代理商预设
const handleSwitchPreset = async (presetId: string) => {
  try {
    switching.value = presetId;
    console.log('Switching to preset:', presetId);
    await switchProvider(currentEngineName.value, presetId);
    toast({
      title: '切换成功',
      description: '已切换到选定的代理商配置',
    });
    // 重新加载当前配置
    await loadCurrentConfig();
  } catch (error) {
    console.error('Failed to switch preset:', error);
    toast({
      title: '切换失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    });
  } finally {
    switching.value = null;
  }
};

// 添加代理商预设
const handleAddPreset = () => {
  showNewPresetDialog.value = true;
};

// 创建代理商预设
const handleCreatePreset = async (presetData: ProviderPresetCreateRequest) => {
  try {
    console.log('Creating preset:', presetData);
    await createProviderPreset(currentEngineName.value, presetData);
    toast({
      title: '添加成功',
      description: '代理商预设已添加',
    });
    // 重新加载预设列表
    await loadProviderPresets();
  } catch (error) {
    console.error('Failed to create preset:', error);
    toast({
      title: '添加失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    });
  }
};

// 监听引擎切换
watch(activeEngineTab, () => {
  loadCurrentConfig();
  loadProviderPresets();
});

// 组件挂载时加载配置
onMounted(() => {
  if (currentView.value === 'engines') {
    loadCurrentConfig();
    loadProviderPresets();
  }
});

const headerTitle = computed(() => {
  if (currentView.value === 'main') return '设置';
  if (currentView.value === 'engines') return '引擎配置';
  if (currentView.value === 'plugins') return '插件';
  if (currentView.value === 'subagents') return '子代理';
  if (currentView.value === 'skills') return '技能';
  return '设置';
});

const showAddButton = computed(() => {
  return false; // 所有页面都不显示添加按钮
});

const handleBack = () => {
  currentView.value = 'main';
};

const handleItemClick = (item: SettingItem) => {
  if (item.action) {
    currentView.value = item.action as ViewType;
  } else {
    toast({ title: '功能开发中', description: `${item.label} 功能正在开发中` });
  }
};

const handleAddAction = () => {
  toast({ title: '功能开发中', description: '添加功能正在开发中' });
};

const handleSwitchEngine = (engine: string) => {
  toast({ title: '切换引擎', description: `已切换到 ${engine}` });
};

// ============= Plugins 相关函数 =============

// 加载插件列表
const loadPlugins = async () => {
  loadingPlugins.value = true;
  try {
    const response = await listPlugins();
    plugins.value = response.plugins;
  } catch (error) {
    console.error('Failed to load plugins:', error);
    toast({
      title: '加载插件失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    });
  } finally {
    loadingPlugins.value = false;
  }
};

// 切换插件启用状态
const handleTogglePlugin = async (pluginId: string, enabled: boolean) => {
  try {
    if (enabled) {
      await enablePlugin(pluginId);
    } else {
      await disablePlugin(pluginId);
    }
    toast({
      title: enabled ? '已启用' : '已禁用',
      description: `插件 ${pluginId} 已${enabled ? '启用' : '禁用'}`,
    });
    // 重新加载列表
    await loadPlugins();
  } catch (error) {
    console.error('Failed to toggle plugin:', error);
    toast({
      title: '操作失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    });
  }
};

// ============= Agents 相关函数 =============

// 加载代理列表
const loadAgents = async () => {
  loadingAgents.value = true;
  try {
    const response = await listAgents();
    agents.value = response.agents;
  } catch (error) {
    console.error('Failed to load agents:', error);
    toast({
      title: '加载代理失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    });
  } finally {
    loadingAgents.value = false;
  }
};

// 切换代理启用状态
const handleToggleAgent = async (agentId: string, enabled: boolean) => {
  try {
    if (enabled) {
      await enableAgent(agentId);
    } else {
      await disableAgent(agentId);
    }
    toast({
      title: enabled ? '已启用' : '已禁用',
      description: `代理 ${agentId} 已${enabled ? '启用' : '禁用'}`,
    });
    // 重新加载列表
    await loadAgents();
  } catch (error) {
    console.error('Failed to toggle agent:', error);
    toast({
      title: '操作失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    });
  }
};

// ============= Skills 相关函数 =============

// 加载技能列表
const loadSkills = async () => {
  loadingSkills.value = true;
  try {
    const response = await listSkills();
    skills.value = response.skills;
  } catch (error) {
    console.error('Failed to load skills:', error);
    toast({
      title: '加载技能失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    });
  } finally {
    loadingSkills.value = false;
  }
};

// 切换技能启用状态
const handleToggleSkill = async (skillId: string, enabled: boolean) => {
  try {
    if (enabled) {
      await enableSkill(skillId);
    } else {
      await disableSkill(skillId);
    }
    toast({
      title: enabled ? '已启用' : '已禁用',
      description: `技能 ${skillId} 已${enabled ? '启用' : '禁用'}`,
    });
    // 重新加载列表
    await loadSkills();
  } catch (error) {
    console.error('Failed to toggle skill:', error);
    toast({
      title: '操作失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    });
  }
};

// 查看插件详情
const handleViewPluginDetail = (plugin: Plugin) => {
  selectedItem.value = plugin;
  selectedItemType.value = 'plugin';
  showDetailDialog.value = true;
};

// 查看代理详情
const handleViewAgentDetail = (agent: Agent) => {
  selectedItem.value = agent;
  selectedItemType.value = 'agent';
  showDetailDialog.value = true;
};

// 查看技能详情
const handleViewSkillDetail = (skill: Skill) => {
  selectedItem.value = skill;
  selectedItemType.value = 'skill';
  showDetailDialog.value = true;
};

// ============= 视图切换监听 =============

// 监听视图切换，自动加载对应数据
watch(currentView, async (newView) => {
  if (newView === 'engines') {
    loadCurrentConfig();
    loadProviderPresets();
  } else if (newView === 'plugins') {
    await loadPlugins();
  } else if (newView === 'subagents') {
    await loadAgents();
  } else if (newView === 'skills') {
    await loadSkills();
  }
});
</script>
