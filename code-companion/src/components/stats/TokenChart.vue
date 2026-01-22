<template>
  <div class="space-y-4">
    <div class="grid grid-cols-3 gap-3">
      <button
        @click="handlePeriodClick('today')"
        class="p-3 rounded-lg border transition-colors text-left"
        :class="selectedPeriod === 'today'
          ? 'bg-primary/10 border-primary'
          : 'bg-card border-border hover:border-primary/50'"
      >
        <p class="text-[10px] text-muted-foreground mb-1">今日</p>
        <p class="text-lg font-semibold">{{ (stats.today / 1000).toFixed(1) }}K</p>
        <p class="text-xs text-accent">${{ stats.costBreakdown[0].cost.toFixed(2) }}</p>
      </button>
      <button
        @click="handlePeriodClick('week')"
        class="p-3 rounded-lg border transition-colors text-left"
        :class="selectedPeriod === 'week'
          ? 'bg-primary/10 border-primary'
          : 'bg-card border-border hover:border-primary/50'"
      >
        <p class="text-[10px] text-muted-foreground mb-1">本周</p>
        <p class="text-lg font-semibold">{{ (stats.thisWeek / 1000).toFixed(1) }}K</p>
        <p class="text-xs text-accent">${{ stats.costBreakdown[1].cost.toFixed(2) }}</p>
      </button>
      <button
        @click="handlePeriodClick('month')"
        class="p-3 rounded-lg border transition-colors text-left"
        :class="selectedPeriod === 'month'
          ? 'bg-primary/10 border-primary'
          : 'bg-card border-border hover:border-primary/50'"
      >
        <p class="text-[10px] text-muted-foreground mb-1">本月</p>
        <p class="text-lg font-semibold">{{ (stats.thisMonth / 1000).toFixed(1) }}K</p>
        <p class="text-xs text-accent">${{ stats.costBreakdown[2].cost.toFixed(2) }}</p>
      </button>
    </div>

    <div class="p-4 rounded-lg bg-card border border-border">
      <h3 class="text-sm font-medium mb-4">按引擎统计</h3>
      <div class="space-y-3">
        <div v-for="(tokens, engine) in stats.byEngine" :key="engine">
          <div class="flex items-center justify-between text-xs mb-1">
            <span class="capitalize font-medium">{{ engine }}</span>
            <span class="text-muted-foreground">{{ (tokens / 1000).toFixed(0) }}K</span>
          </div>
          <div class="h-2 bg-secondary rounded-full overflow-hidden">
            <div
              class="h-full rounded-full"
              :class="engineColors[engine]"
              :style="{ width: `${(tokens / stats.thisMonth) * 100}%` }"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="p-4 rounded-lg bg-card border border-border">
      <h3 class="text-sm font-medium mb-4">Token 用量趋势</h3>
      <div class="flex items-end justify-around h-32 gap-4">
        <div v-for="item in stats.costBreakdown" :key="item.period" class="flex flex-col items-center gap-2 flex-1">
          <div
            class="w-full bg-primary/20 rounded-t relative transition-all"
            :style="{
              height: maxTokens > 0 ? `${Math.max((item.tokens / maxTokens) * 100, 2)}%` : '2%',
              minHeight: '8px'
            }"
          >
            <div
              class="absolute inset-0 bg-gradient-to-t from-primary to-primary/50 rounded-t"
            />
          </div>
          <span class="text-[10px] text-muted-foreground">{{ item.period }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { TokenStats } from '@/types';

const props = defineProps<{
  stats: TokenStats;
  selectedPeriod: 'today' | 'week' | 'month' | null;
}>();

const emit = defineEmits<{
  'period-change': [period: 'today' | 'week' | 'month' | null];
}>();

// 点击时间段，如果已选中则取消选择
const handlePeriodClick = (period: 'today' | 'week' | 'month') => {
  if (props.selectedPeriod === period) {
    emit('period-change', null); // 取消选择
  } else {
    emit('period-change', period); // 选择新的时间段
  }
};

const maxTokens = computed(() => Math.max(...props.stats.costBreakdown.map(b => b.tokens)));

const engineColors: Record<string, string> = {
  claude: 'bg-orange-500',
  codex: 'bg-emerald-500',
  gemini: 'bg-blue-500',
};
</script>
