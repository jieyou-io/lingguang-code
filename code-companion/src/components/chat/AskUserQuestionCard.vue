<template>
  <div class="my-2 p-4 rounded-lg border border-primary/30 bg-primary/5">
    <div class="flex items-start gap-3">
      <div class="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
        <HelpCircle class="w-4 h-4 text-primary" />
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-2">
          <span class="font-medium text-primary">AI 需要您的帮助</span>
        </div>

        <!-- 问题列表 -->
        <div class="space-y-4">
          <div v-for="(question, qIndex) in questions" :key="qIndex" class="space-y-2">
            <div class="flex items-center gap-2">
              <span v-if="question.header" class="text-xs px-2 py-0.5 rounded bg-primary/20 text-primary">
                {{ question.header }}
              </span>
            </div>
            <p class="text-sm text-foreground">{{ question.question }}</p>

            <!-- 选项 -->
            <div v-if="!responded" class="space-y-1.5">
              <template v-if="question.multiSelect">
                <!-- 多选 -->
                <label
                  v-for="(option, optIndex) in question.options"
                  :key="optIndex"
                  class="flex items-start gap-2 p-2 rounded-lg border border-border hover:bg-secondary/50 cursor-pointer transition-colors"
                >
                  <input
                    type="checkbox"
                    :value="option.label"
                    v-model="answers[qIndex]"
                    class="mt-0.5 accent-primary"
                  />
                  <div class="flex-1">
                    <div class="text-sm font-medium">{{ option.label }}</div>
                    <div v-if="option.description" class="text-xs text-muted-foreground">
                      {{ option.description }}
                    </div>
                  </div>
                </label>
              </template>
              <template v-else>
                <!-- 单选 -->
                <label
                  v-for="(option, optIndex) in question.options"
                  :key="optIndex"
                  class="flex items-start gap-2 p-2 rounded-lg border border-border hover:bg-secondary/50 cursor-pointer transition-colors"
                  :class="{ 'bg-primary/10 border-primary/50': answers[qIndex] === option.label }"
                >
                  <input
                    type="radio"
                    :name="`question_${qIndex}`"
                    :value="option.label"
                    v-model="answers[qIndex]"
                    class="mt-0.5 accent-primary"
                  />
                  <div class="flex-1">
                    <div class="text-sm font-medium">{{ option.label }}</div>
                    <div v-if="option.description" class="text-xs text-muted-foreground">
                      {{ option.description }}
                    </div>
                  </div>
                </label>
              </template>

              <!-- 自定义输入 -->
              <div class="mt-2">
                <label class="flex items-center gap-2 text-xs text-muted-foreground mb-1 cursor-pointer">
                  <input type="checkbox" v-model="showOther[qIndex]" class="accent-primary" />
                  其他（自定义）
                </label>
                <input
                  v-if="showOther[qIndex]"
                  type="text"
                  v-model="otherInput[qIndex]"
                  placeholder="请输入..."
                  class="w-full px-3 py-2 text-sm bg-secondary border border-border rounded-lg focus:outline-none focus:border-primary transition-colors"
                />
              </div>
            </div>

            <!-- 已回答状态 -->
            <div v-else class="text-sm text-muted-foreground">
              <span class="text-primary">已选择：</span>
              {{ formatAnswer(qIndex) }}
            </div>
          </div>
        </div>

        <!-- 提交按钮 -->
        <div v-if="!responded" class="flex items-center gap-2 mt-4">
          <button
            @click="handleSubmit"
            :disabled="!isValid || loading"
            class="flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send class="w-3.5 h-3.5" />
            提交答案
          </button>
          <span v-if="loading" class="text-xs text-muted-foreground">
            处理中...
          </span>
        </div>

        <!-- 已提交状态 -->
        <div v-else class="flex items-center gap-2 mt-3">
          <span class="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-green-500/20 text-green-500">
            <Check class="w-3.5 h-3.5" />
            已提交答案
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { HelpCircle, Send, Check } from 'lucide-vue-next';

interface QuestionOption {
  label: string;
  description?: string;
}

interface Question {
  question: string;
  header?: string;
  options: QuestionOption[];
  multiSelect?: boolean;
}

const props = defineProps<{
  toolId: string;
  questions: Question[];
}>();

const emit = defineEmits<{
  submit: [answers: Record<string, any>];
}>();

const loading = ref(false);
const responded = ref(false);
const answers = ref<Record<number, any>>({});
const showOther = ref<Record<number, boolean>>({});
const otherInput = ref<Record<number, string>>({});

// 初始化多选题答案为数组
watch(() => props.questions, (qs) => {
  qs.forEach((q, i) => {
    if (q.multiSelect) {
      answers.value[i] = [];
    }
  });
}, { immediate: true });

const isValid = computed(() => {
  return props.questions.every((q, i) => {
    const answer = answers.value[i];
    const other = showOther.value[i] && otherInput.value[i];
    if (q.multiSelect) {
      return (Array.isArray(answer) && answer.length > 0) || other;
    }
    return answer || other;
  });
});

const formatAnswer = (index: number) => {
  const answer = answers.value[index];
  const other = showOther.value[index] && otherInput.value[index];

  if (Array.isArray(answer)) {
    const combined = [...answer];
    if (other) combined.push(other);
    return combined.join(', ');
  }

  return other || answer || '';
};

const handleSubmit = async () => {
  if (!isValid.value) return;

  loading.value = true;
  try {
    // 构建答案对象
    const result: Record<string, any> = {};
    props.questions.forEach((q, i) => {
      let answer = answers.value[i];
      const other = showOther.value[i] && otherInput.value[i];

      if (q.multiSelect && Array.isArray(answer)) {
        if (other) answer = [...answer, other];
        result[`question_${i}`] = answer;
      } else {
        result[`question_${i}`] = other || answer;
      }
    });

    emit('submit', result);
    responded.value = true;
  } finally {
    loading.value = false;
  }
};
</script>
