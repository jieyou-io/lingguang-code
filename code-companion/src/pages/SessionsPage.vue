<template>
  <AppShell>
    <Header
      :title="currentProject.name"
      :subtitle="`${activeSessions.length} 个活跃会话`"
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <button
            class="p-2 rounded-lg hover:bg-secondary transition-colors"
            title="打开 IDE"
          >
            <Code2 :size="20" class="text-muted-foreground" />
          </button>
          <button
            @click="handleNewSession"
            class="p-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus :size="20" />
          </button>
        </div>
      </template>
    </Header>

    <div class="p-4 space-y-6">
      <!-- Quick stats -->
      <div class="flex gap-3 overflow-x-auto scrollbar-hide -mx-4 px-4">
        <div class="flex-1 min-w-[140px] px-4 py-3 rounded-lg bg-card border border-border">
          <p class="text-[10px] text-muted-foreground mb-0.5">今日 Tokens</p>
          <p class="text-lg font-semibold">{{ formatNumber(stats.todayTokens) }}</p>
        </div>
        <div class="flex-1 min-w-[140px] px-4 py-3 rounded-lg bg-card border border-border">
          <p class="text-[10px] text-muted-foreground mb-0.5">今日成本</p>
          <p class="text-lg font-semibold">${{ stats.todayCost.toFixed(2) }}</p>
        </div>
        <div class="flex-1 min-w-[140px] px-4 py-3 rounded-lg bg-card border border-border">
          <p class="text-[10px] text-muted-foreground mb-0.5">本周会话</p>
          <p class="text-lg font-semibold">{{ stats.weekSessions }}</p>
        </div>
      </div>

      <!-- 引擎过滤标签 -->
      <div v-if="projectId" class="flex gap-2 overflow-x-auto scrollbar-hide">
        <button
          @click="selectedEngine = null"
          :class="[
            'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap',
            selectedEngine === null
              ? 'bg-primary text-primary-foreground'
              : 'bg-secondary text-muted-foreground hover:bg-secondary/80'
          ]"
        >
          全部
        </button>
        <button
          @click="selectedEngine = 'claude'"
          :class="[
            'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap',
            selectedEngine === 'claude'
              ? 'bg-primary text-primary-foreground'
              : 'bg-secondary text-muted-foreground hover:bg-secondary/80'
          ]"
        >
          Claude Code
        </button>
        <button
          @click="selectedEngine = 'codex'"
          :class="[
            'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap',
            selectedEngine === 'codex'
              ? 'bg-primary text-primary-foreground'
              : 'bg-secondary text-muted-foreground hover:bg-secondary/80'
          ]"
        >
          Codex
        </button>
        <button
          @click="selectedEngine = 'gemini'"
          :class="[
            'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap',
            selectedEngine === 'gemini'
              ? 'bg-primary text-primary-foreground'
              : 'bg-secondary text-muted-foreground hover:bg-secondary/80'
          ]"
        >
          Gemini
        </button>
      </div>

      <div v-if="isLoading && projectId" class="flex items-center justify-center py-12">
        <div class="animate-pulse text-muted-foreground">加载中...</div>
      </div>

      <!-- 没有项目ID时的提示 -->
      <div
        v-else-if="!projectId"
        class="flex flex-col items-center justify-center py-12 text-center"
      >
        <p class="text-muted-foreground mb-4">请先选择一个项目</p>
        <button
          @click="router.push('/projects')"
          class="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <span>选择项目</span>
        </button>
      </div>

      <div
        v-else-if="projectSessions.length === 0"
        class="flex flex-col items-center justify-center py-12 text-center"
      >
        <p class="text-muted-foreground mb-4">暂无会话记录</p>
        <button
          @click="handleNewSession"
          class="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus :size="16" />
          <span>开始新会话</span>
        </button>
      </div>

      <template v-else>
        <!-- Active sessions -->
        <section v-if="activeSessions.length > 0">
          <h2 class="text-sm font-medium text-muted-foreground mb-3">活跃会话</h2>
          <SessionList
            :sessions="activeSessions"
            @click="handleSessionClick"
            @delete="handleDeleteSession"
            @view-code="handleViewCode"
          />
        </section>

        <!-- Completed sessions -->
        <section v-if="completedSessions.length > 0">
          <h2 class="text-sm font-medium text-muted-foreground mb-3">已完成</h2>
          <SessionList
            :sessions="completedSessions"
            @click="handleSessionClick"
            @delete="handleDeleteSession"
            @view-code="handleViewCode"
          />
        </section>
      </template>
    </div>

  <CodeFileBrowserDialog
    v-model:open="codeDialogOpen"
    :project-name="currentProject.name"
    :project-path="projectPath"
    :file-tree="fileTree"
  />
  </AppShell>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { Plus, Code2 } from 'lucide-vue-next';
import AppShell from '@/components/layout/AppShell.vue';
import Header from '@/components/layout/Header.vue';
import SessionList from '@/components/session/SessionList.vue';
import CodeFileBrowserDialog from '@/components/project/CodeFileBrowserDialog.vue';
import { useSessions } from '@/composables/useSessions';
import { useToast } from '@/composables/useToast';
import { getQuickStats, type QuickStatsResponse } from '@/lib/usage-api';
import { getProjectFileTree } from '@/lib/services/project-files';
import { ProjectFileNode } from '@/types';

const router = useRouter();
const route = useRoute();
const { toast } = useToast();

// 从路由获取项目路径参数（URL 编码格式）
const encodedProjectPath = route.params.projectId as string || '';

// 解码 URL 编码的路径参数，得到完整的文件系统路径
// 例如: %2FUsers%2Fking%2FDocuments%2Fai-code%2Fmobile%2FAny-code -> /Users/king/Documents/ai-code/mobile/Any-code
let decodedPath = '';
if (encodedProjectPath) {
  try {
    decodedPath = decodeURIComponent(encodedProjectPath);
  } catch (e) {
    console.error('Failed to decode project path:', e);
  }
}

const projectPath = computed(() => decodedPath);

// 将完整路径转换为项目 ID 格式（用于会话 API）
// 🔥 编码规则：先把 - 转为 --，再把 / 转为 -
// 例如: /Users/king/Documents/ai-code/mobile/Any-code -> -Users-king-Documents-ai--code-mobile-Any--code
const projectId = decodedPath
  ? decodedPath.replace(/-/g, '--').replace(/\//g, '-')
  : '';

// 使用真实 API 数据（仅当有 projectId 时）
// 🔥 传递 projectPath 用于过滤 Codex/Gemini 会话
const { sessions, loading: isLoading, error, loadSessions, removeSession } = projectId
  ? useSessions(projectId, projectPath.value)
  : { sessions: ref([]), loading: ref(false), error: ref(null), loadSessions: () => {}, removeSession: async () => {} };

const codeDialogOpen = ref(false);
const selectedEngine = ref<string | null>(null);
const fileTree = ref<ProjectFileNode[]>([]);
const fileTreeLoading = ref(false);

// 快速统计数据
const quickStats = ref<QuickStatsResponse | null>(null);
const loadingStats = ref(false);

// 加载快速统计
const loadQuickStats = async () => {
  if (!projectPath.value) return;

  console.log('[SessionsPage] Loading quick stats for project:', projectPath.value);
  loadingStats.value = true;
  try {
    quickStats.value = await getQuickStats(projectPath.value);
    console.log('[SessionsPage] Quick stats loaded:', quickStats.value);
  } catch (err) {
    console.error('Failed to load quick stats:', err);
    // 静默失败，使用计算的统计数据作为降级
  } finally {
    loadingStats.value = false;
  }
};

// 当前项目信息（简化版）
const currentProject = computed(() => ({
  id: projectId,
  name: projectPath.value || '所有会话',
}));

const projectSessions = computed(() => {
  if (!selectedEngine.value) {
    return sessions.value;
  }
  return sessions.value.filter(s => s.engine === selectedEngine.value);
});

const activeSessions = computed(() =>
  projectSessions.value.filter(s => s.status === 'active' || s.status === 'paused')
);

const completedSessions = computed(() =>
  projectSessions.value.filter(s => s.status === 'completed')
);

const stats = computed(() => {
  // 优先使用 API 返回的真实统计数据
  if (quickStats.value) {
    return {
      todayTokens: quickStats.value.today.tokens,
      todayCost: quickStats.value.today.cost,
      weekSessions: quickStats.value.week.sessions,
    };
  }

  // 降级：从本地会话数据计算（可能不准确）
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const todaySessions = projectSessions.value.filter(s =>
    new Date(s.updatedAt) >= today
  );

  const todayTokens = todaySessions.reduce((sum, s) => sum + (s.tokenCount || 0), 0);
  const todayCost = todaySessions.reduce((sum, s) => sum + (s.cost || 0), 0);

  const weekStart = new Date(today);
  weekStart.setDate(weekStart.getDate() - 7);
  const weekSessions = projectSessions.value.filter(s =>
    new Date(s.updatedAt) >= weekStart
  ).length;

  return { todayTokens, todayCost, weekSessions };
});

onMounted(() => {
  loadSessions();
  loadQuickStats();
});

// 监听 projectId 变化，重新加载统计
watch(() => projectId, () => {
  loadQuickStats();
});

const handleNewSession = () => {
  const newSessionId = Date.now().toString();
  // 🔥 修复：传递 projectId 和选择的引擎
  const engine = selectedEngine.value || 'claude';
  router.push(`/chat/${projectId}/${newSessionId}?engine=${engine}`);
};

const handleSessionClick = (session: any) => {
  // 🔥 传递 engine 参数，避免历史加载时重新查找引擎类型
  const engine = session.engine || 'claude';
  router.push(`/chat/${projectId}/${session.id}?engine=${engine}`);
};

const handleDeleteSession = async (sessionId: string) => {
  try {
    await removeSession(sessionId);
    toast({
      title: '会话已删除',
      description: '历史记录已清除',
    });
  } catch (err) {
    toast({
      title: '删除失败',
      description: error.value || '无法删除会话',
      variant: 'destructive',
    });
  }
};

const handleViewCode = () => {
  codeDialogOpen.value = true;
};

const loadFileTree = async () => {
  if (!projectPath.value) return;
  fileTreeLoading.value = true;
  try {
    fileTree.value = await getProjectFileTree(projectPath.value);
  } catch (error) {
    console.error('Failed to load file tree:', error);
    fileTree.value = [];
  } finally {
    fileTreeLoading.value = false;
  }
};

watch([codeDialogOpen, projectPath], ([open, path]) => {
  if (open && path) {
    loadFileTree();
  }
});

const formatNumber = (num: number) => {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
};
</script>
