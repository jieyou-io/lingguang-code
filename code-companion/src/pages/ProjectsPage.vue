<template>
  <AppShell>
    <Header title="项目">
      <template #actions>
        <button class="p-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
          <Plus class="w-5 h-5" />
        </button>
      </template>
    </Header>

    <div class="p-4 space-y-4">
      <div class="relative">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索项目..."
          class="w-full pl-10 pr-4 py-2.5 bg-secondary rounded-lg border border-border text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 transition-colors"
        />
      </div>

      <div class="p-4 rounded-lg bg-gradient-to-br from-primary/10 to-transparent border border-primary/20">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs text-muted-foreground mb-1">本月总消耗</p>
            <p class="text-2xl font-bold text-primary">${{ totalStats.cost.toFixed(2) }}</p>
          </div>
          <div class="text-right">
            <p class="text-xs text-muted-foreground mb-1">总 Tokens</p>
            <p class="text-lg font-semibold">{{ (totalStats.tokens / 1000).toFixed(1) }}K</p>
          </div>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="text-center py-8 text-muted-foreground">
        <p>加载中...</p>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive">
        <p>{{ error }}</p>
        <button @click="loadProjects" class="mt-2 text-sm underline">重试</button>
      </div>

      <!-- 项目列表 -->
      <div v-else class="space-y-3">
        <div v-for="(project, index) in filteredProjects" :key="project.id" :style="{ animationDelay: `${index * 50}ms` }">
          <ProjectCard
            :project="project"
            :on-click="() => handleOpen(project)"
            :on-bind-notification="() => handleBindNotification(project)"
            :on-view-code="() => handleViewCode(project)"
          />
        </div>
      </div>
    </div>

    <NotificationBindingDialog
      v-if="selectedProject"
      :open="notificationDialogOpen"
      :project-name="selectedProject.name"
      :project-id="selectedProject.id"
      :on-open-change="(value) => (notificationDialogOpen = value)"
    />

    <CodeFileBrowserDialog
      v-if="selectedProject"
      :open="codeFileBrowserOpen"
      :project-name="selectedProject.name"
      @update:open="codeFileBrowserOpen = $event"
    />
  </AppShell>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Plus, Search } from 'lucide-vue-next';
import AppShell from '@/components/layout/AppShell.vue';
import Header from '@/components/layout/Header.vue';
import ProjectCard from '@/components/project/ProjectCard.vue';
import NotificationBindingDialog from '@/components/project/NotificationBindingDialog.vue';
import CodeFileBrowserDialog from '@/components/project/CodeFileBrowserDialog.vue';
import { useProjects } from '@/composables/useProjects';
import { Project } from '@/types';
import { getQuickStats, type QuickStatsResponse } from '@/lib/usage-api';

const router = useRouter();
const searchQuery = ref('');
const notificationDialogOpen = ref(false);
const codeFileBrowserOpen = ref(false);
const selectedProject = ref<Project | null>(null);

// 使用真实 API 数据
const { projects, loading, error, loadProjects } = useProjects();

// 快速统计数据（全局，不传 project_path）
const quickStats = ref<QuickStatsResponse | null>(null);
const loadingStats = ref(false);

// 加载全局快速统计
const loadQuickStats = async () => {
  loadingStats.value = true;
  try {
    quickStats.value = await getQuickStats(); // 不传 project_path，获取全局统计
  } catch (err) {
    console.error('Failed to load quick stats:', err);
    // 静默失败，使用计算的统计数据作为降级
  } finally {
    loadingStats.value = false;
  }
};

// 计算总统计数据
const totalStats = computed(() => {
  // 优先使用 API 返回的本月统计数据
  if (quickStats.value) {
    return {
      cost: quickStats.value.month.cost,
      tokens: quickStats.value.month.tokens,
    };
  }

  // 降级：从项目列表累加（可能不准确）
  const total = projects.value.reduce(
    (acc, p) => ({
      cost: acc.cost + p.totalCost,
      tokens: acc.tokens + p.totalTokens,
    }),
    { cost: 0, tokens: 0 }
  );
  return total;
});

const filteredProjects = computed(() =>
  projects.value.filter(p => p.name.toLowerCase().includes(searchQuery.value.toLowerCase()))
);

// 页面加载时获取数据
onMounted(() => {
  loadProjects();
  loadQuickStats();
});

const handleBindNotification = (project: Project) => {
  selectedProject.value = project;
  notificationDialogOpen.value = true;
};

const handleViewCode = (project: Project) => {
  selectedProject.value = project;
  codeFileBrowserOpen.value = true;
};

const handleOpen = (project: Project) => {
  // 使用 path 而不是 id，因为 path 是完整的文件系统路径
  // 需要将路径编码为 URL 安全格式
  const encodedPath = encodeURIComponent(project.path);
  router.push(`/sessions/${encodedPath}`);
};
</script>
