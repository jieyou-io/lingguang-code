<template>
  <AppShell>
    <Header title="使用统计" />

    <div class="p-4 space-y-4">
      <div class="space-y-2">
        <div class="flex items-center gap-2 text-sm text-muted-foreground">
          <Cpu class="w-4 h-4" />
          <span>引擎状态</span>
          <button
            v-if="!loadingEngineStatus"
            @click="refreshEngineStatus"
            class="ml-auto p-1 rounded hover:bg-secondary transition-colors"
            title="刷新状态"
          >
            <RefreshCw class="w-4 h-4" />
          </button>
        </div>
        <div v-if="loadingEngineStatus" class="p-8 text-center text-muted-foreground">
          <p class="text-sm">加载中...</p>
        </div>
        <div v-else-if="engineStatusError" class="p-4 rounded-lg bg-destructive/10 text-destructive text-sm">
          加载失败: {{ engineStatusError }}
        </div>
        <div v-else class="grid grid-cols-3 gap-2">
          <div
            v-for="engine in engineStatuses"
            :key="engine.engine"
            class="p-3 rounded-lg bg-card border border-border"
          >
            <div class="flex items-center gap-2 mb-1">
              <StatusDot
                :status="engine.status === 'online' ? 'active' : engine.status === 'degraded' ? 'paused' : 'error'"
              />
              <span class="text-xs font-medium truncate">{{ engine.name }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-xs" :class="getStatusColor(engine.status)">
                {{ getStatusText(engine.status) }}
              </span>
              <span class="text-xs text-muted-foreground">{{ engine.latency }}ms</span>
            </div>
            <p v-if="engine.message" class="text-xs text-muted-foreground mt-1 truncate" :title="engine.message">
              {{ engine.message }}
            </p>
          </div>
        </div>
      </div>

      <TokenChart
        :stats="tokenStats"
        :selected-period="selectedPeriod"
        @period-change="handlePeriodChange"
      />
    </div>
  </AppShell>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { Cpu, RefreshCw } from 'lucide-vue-next';
import AppShell from '@/components/layout/AppShell.vue';
import Header from '@/components/layout/Header.vue';
import TokenChart from '@/components/stats/TokenChart.vue';
import StatusDot from '@/components/icons/StatusDot.vue';
import { getEnginesStatus, type EngineStatus } from '@/lib/engine-status-api';
import { getUsageStats, type UsageStatsResponse } from '@/lib/usage-api';
import { TokenStats } from '@/types';

const engineStatuses = ref<EngineStatus[]>([]);
const loadingEngineStatus = ref(false);
const engineStatusError = ref<string | null>(null);

// 时间筛选：'today' | 'week' | 'month' | null（null 表示查全部）
type TimePeriod = 'today' | 'week' | 'month' | null;
const selectedPeriod = ref<TimePeriod>('today');

// 使用统计数据
const usageStats = ref<UsageStatsResponse | null>(null);
const loadingUsageStats = ref(false);
const usageStatsError = ref<string | null>(null);

// 加载使用统计
const loadUsageStats = async () => {
  loadingUsageStats.value = true;
  usageStatsError.value = null;

  try {
    usageStats.value = await getUsageStats(); // 不传 days，获取全部统计
  } catch (error) {
    console.error('Failed to load usage stats:', error);
    usageStatsError.value = error instanceof Error ? error.message : '未知错误';
  } finally {
    loadingUsageStats.value = false;
  }
};

// 转换为 TokenStats 格式供 TokenChart 使用
const tokenStats = computed<TokenStats>(() => {
  if (!usageStats.value) {
    // 返回空数据
    return {
      today: 0,
      thisWeek: 0,
      thisMonth: 0,
      byEngine: {
        claude: 0,
        codex: 0,
        gemini: 0,
      },
      costBreakdown: [
        { period: '今日', tokens: 0, cost: 0 },
        { period: '本周', tokens: 0, cost: 0 },
        { period: '本月', tokens: 0, cost: 0 },
      ],
    };
  }

  const stats = usageStats.value;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const weekStart = new Date(today);
  weekStart.setDate(weekStart.getDate() - today.getDay()); // 本周日
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);

  // 从 by_date 计算今日/本周/本月 tokens
  let todayTokens = 0;
  let todayCost = 0;
  let weekTokens = 0;
  let weekCost = 0;
  let monthTokens = 0;
  let monthCost = 0;

  stats.by_date.forEach(daily => {
    const date = new Date(daily.date);
    if (date >= today) {
      todayTokens += daily.total_tokens;
      todayCost += daily.total_cost;
    }
    if (date >= weekStart) {
      weekTokens += daily.total_tokens;
      weekCost += daily.total_cost;
    }
    if (date >= monthStart) {
      monthTokens += daily.total_tokens;
      monthCost += daily.total_cost;
    }
  });

  // 根据选中的时间段过滤引擎统计数据
  let filteredByEngine = { claude: 0, codex: 0, gemini: 0 };

  if (selectedPeriod.value === null) {
    // 不选择时间段，显示全部数据
    filteredByEngine = stats.by_engine as { claude: number; codex: number; gemini: number };
  } else {
    // 根据选中的时间段，从 by_date 重新计算引擎统计
    const startDate = selectedPeriod.value === 'today' ? today :
                      selectedPeriod.value === 'week' ? weekStart : monthStart;

    stats.by_date.forEach(daily => {
      const date = new Date(daily.date);
      if (date >= startDate) {
        // 这里简化处理，使用总 tokens 按比例分配
        // 实际应该从后端获取按时间段和引擎的详细统计
        const ratio = daily.total_tokens / stats.total_tokens;
        filteredByEngine.claude += (stats.by_engine.claude || 0) * ratio;
        filteredByEngine.codex += (stats.by_engine.codex || 0) * ratio;
        filteredByEngine.gemini += (stats.by_engine.gemini || 0) * ratio;
      }
    });
  }

  return {
    today: todayTokens,
    thisWeek: weekTokens,
    thisMonth: monthTokens,
    byEngine: filteredByEngine,
    costBreakdown: [
      { period: '今日', tokens: todayTokens, cost: todayCost },
      { period: '本周', tokens: weekTokens, cost: weekCost },
      { period: '本月', tokens: monthTokens, cost: monthCost },
    ],
  };
});

const loadEngineStatus = async () => {
  loadingEngineStatus.value = true;
  engineStatusError.value = null;

  try {
    const response = await getEnginesStatus();
    engineStatuses.value = response.engines;
  } catch (error) {
    console.error('Failed to load engine status:', error);
    engineStatusError.value = error instanceof Error ? error.message : '未知错误';
  } finally {
    loadingEngineStatus.value = false;
  }
};

const refreshEngineStatus = async () => {
  await loadEngineStatus();
};

const getStatusColor = (status: EngineStatus['status']) => {
  switch (status) {
    case 'online':
      return 'text-green-500';
    case 'degraded':
      return 'text-yellow-500';
    case 'offline':
      return 'text-destructive';
  }
};

const getStatusText = (status: EngineStatus['status']) => {
  switch (status) {
    case 'online':
      return '正常';
    case 'degraded':
      return '延迟';
    case 'offline':
      return '离线';
  }
};

// 处理时间筛选切换
const handlePeriodChange = (period: TimePeriod) => {
  selectedPeriod.value = period;
};

// 加载引擎状态
onMounted(() => {
  loadEngineStatus();
  loadUsageStats();
});
</script>
