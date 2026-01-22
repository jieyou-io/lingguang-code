<template>
  <AppShell>
    <Header title="MCP 工具">
      <template #actions>
        <button
          class="p-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          @click="handleAdd"
        >
          <Plus class="w-5 h-5" />
        </button>
      </template>
    </Header>

    <div class="p-4">
      <div class="grid grid-cols-3 gap-2 mb-4">
        <button
          v-for="engine in engineConfig"
          :key="engine.id"
          class="px-3 py-2 text-xs rounded-lg border transition-colors"
          :class="activeEngine === engine.id ? 'bg-primary text-primary-foreground border-primary' : 'bg-card border-border text-muted-foreground hover:text-foreground'"
          @click="activeEngine = engine.id"
        >
          <span>{{ engine.icon }}</span>
          <span class="ml-1 hidden sm:inline">{{ engine.name }}</span>
          <span class="ml-1 sm:hidden">{{ engine.name.split(' ')[0] }}</span>
        </button>
      </div>

      <div class="space-y-6">
        <div class="flex items-center justify-between text-sm text-muted-foreground">
          <span>{{ activeEngineName }}</span>
          <span>{{ getEnabledCount(activeEngine) }} / {{ getTotalCount(activeEngine) }} 已启用</span>
        </div>

        <section v-if="enabledTools.length > 0">
          <h2 class="text-sm font-medium text-muted-foreground mb-3">
            已启用 ({{ enabledTools.length }})
          </h2>
          <div class="space-y-3">
            <div v-for="(tool, index) in enabledTools" :key="tool.id" :style="{ animationDelay: `${index * 50}ms` }">
              <MCPToolCard :tool="tool" :on-toggle="(enabled) => handleToggle(tool.id, enabled)" />
            </div>
          </div>
        </section>

        <section v-if="disabledTools.length > 0">
          <h2 class="text-sm font-medium text-muted-foreground mb-3">
            已禁用 ({{ disabledTools.length }})
          </h2>
          <div class="space-y-3">
            <div
              v-for="(tool, index) in disabledTools"
              :key="tool.id"
              :style="{ animationDelay: `${(enabledTools.length + index) * 50}ms` }"
            >
              <MCPToolCard :tool="tool" :on-toggle="(enabled) => handleToggle(tool.id, enabled)" />
            </div>
          </div>
        </section>

        <div v-if="loading" class="text-center py-12 text-muted-foreground">
          加载中...
        </div>

        <div v-else-if="servers.length === 0" class="text-center py-12 text-muted-foreground">
          暂无 {{ activeEngineName }} 工具
        </div>
      </div>
    </div>

    <NewMCPServerDialog
      :open="newServerDialogOpen"
      :engine="activeEngine"
      :engine-name="activeEngineName"
      :on-open-change="(value) => (newServerDialogOpen = value)"
      :on-success="loadServers"
    />
  </AppShell>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue';
import { Plus } from 'lucide-vue-next';
import AppShell from '@/components/layout/AppShell.vue';
import Header from '@/components/layout/Header.vue';
import MCPToolCard from '@/components/plugins/MCPToolCard.vue';
import NewMCPServerDialog from '@/components/plugins/NewMCPServerDialog.vue';
import { getMCPServers, updateMCPServer } from '@/lib/services/mcp';
import type { MCPServer, MCPEngine } from '@/types/mcp';
import { useToast } from '@/composables/useToast';

const { toast } = useToast();
const servers = ref<MCPServer[]>([]);
const loading = ref(false);
const activeEngine = ref<MCPEngine>('claude');
const newServerDialogOpen = ref(false);

const engineConfig: { id: MCPEngine; name: string; icon: string }[] = [
  { id: 'claude', name: 'Claude Code', icon: '🟣' },
  { id: 'codex', name: 'Codex', icon: '🟢' },
  { id: 'gemini', name: 'Gemini CLI', icon: '🔵' },
];

const handleToggle = async (id: string, enabled: boolean) => {
  try {
    await updateMCPServer(activeEngine.value, id, { isActive: enabled });
    servers.value = servers.value.map(s => (s.id === id ? { ...s, isActive: enabled } : s));
    toast({
      title: enabled ? '已启用' : '已禁用',
      description: `MCP 服务器已${enabled ? '启用' : '禁用'}`,
    });
  } catch (error) {
    toast({
      title: '操作失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    });
  }
};

const getEnabledCount = (engine: MCPEngine) => servers.value.filter(s => s.isActive).length;
const getTotalCount = (engine: MCPEngine) => servers.value.length;

// 加载服务器列表
const loadServers = async () => {
  loading.value = true;
  try {
    const response = await getMCPServers(activeEngine.value);
    servers.value = response.servers;
  } catch (error) {
    toast({
      title: '加载失败',
      description: error instanceof Error ? error.message : '未知错误',
      variant: 'destructive',
    });
  } finally {
    loading.value = false;
  }
};

const handleAdd = () => {
  newServerDialogOpen.value = true;
};

const enabledTools = computed(() => servers.value.filter(s => s.isActive));
const disabledTools = computed(() => servers.value.filter(s => !s.isActive));
const activeEngineName = computed(() => engineConfig.find(e => e.id === activeEngine.value)?.name || '');

// 组件挂载时加载服务器列表
onMounted(() => {
  loadServers();
});

// 监听引擎切换，重新加载服务器列表
watch(activeEngine, () => {
  loadServers();
});
</script>
