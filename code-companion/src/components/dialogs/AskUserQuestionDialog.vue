<template>
  <div
    v-if="show"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
    @click.self="handleClose"
  >
    <div
      class="w-full max-w-2xl max-h-[80vh] overflow-y-auto bg-background rounded-lg shadow-xl border border-border"
      @click.stop
    >
      <!-- Header -->
      <div class="sticky top-0 bg-background border-b border-border px-6 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <HelpCircle class="w-5 h-5 text-primary" />
            <h2 class="text-lg font-semibold">AI 需要您的帮助</h2>
          </div>
          <button
            @click="handleClose"
            class="p-2 rounded-lg hover:bg-secondary transition-colors"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
        <p class="text-sm text-muted-foreground mt-2">
          请回答以下问题以帮助 AI 更好地完成任务
        </p>
      </div>

      <!-- Questions -->
      <div class="px-6 py-4 space-y-6">
        <div
          v-for="(question, index) in questions"
          :key="index"
          class="space-y-3"
        >
          <!-- Question Header -->
          <div class="space-y-1">
            <h3 class="font-medium text-foreground">
              {{ question.header || `问题 ${index + 1}` }}
            </h3>
            <p class="text-sm text-muted-foreground">
              {{ question.question }}
            </p>
          </div>

          <!-- Options (Radio or Checkbox) -->
          <div v-if="question.options && question.options.length > 0" class="space-y-2">
            <template v-if="question.multiSelect">
              <!-- Multi-select (Checkbox) -->
              <label
                v-for="(option, optIdx) in question.options"
                :key="optIdx"
                class="flex items-start gap-3 p-3 rounded-lg border border-border hover:bg-secondary/50 cursor-pointer transition-colors"
              >
                <input
                  type="checkbox"
                  :value="option.label"
                  v-model="answers[`question_${index}`]"
                  class="mt-0.5 accent-primary"
                />
                <div class="flex-1">
                  <div class="font-medium text-sm">{{ option.label }}</div>
                  <div v-if="option.description" class="text-xs text-muted-foreground mt-1">
                    {{ option.description }}
                  </div>
                </div>
              </label>
            </template>
            <template v-else>
              <!-- Single-select (Radio) -->
              <label
                v-for="(option, optIdx) in question.options"
                :key="optIdx"
                class="flex items-start gap-3 p-3 rounded-lg border border-border hover:bg-secondary/50 cursor-pointer transition-colors"
                :class="{ 'bg-secondary/50 border-primary': answers[`question_${index}`] === option.label }"
              >
                <input
                  type="radio"
                  :name="`question_${index}`"
                  :value="option.label"
                  v-model="answers[`question_${index}`]"
                  class="mt-0.5 accent-primary"
                />
                <div class="flex-1">
                  <div class="font-medium text-sm">{{ option.label }}</div>
                  <div v-if="option.description" class="text-xs text-muted-foreground mt-1">
                    {{ option.description }}
                  </div>
                </div>
              </label>
            </template>

            <!-- "Other" option for text input -->
            <div class="mt-2">
              <label class="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <input
                  type="checkbox"
                  v-model="showOtherInput[index]"
                  class="accent-primary"
                />
                其他（自定义输入）
              </label>
              <input
                v-if="showOtherInput[index]"
                type="text"
                v-model="otherInputs[index]"
                placeholder="请输入您的答案..."
                class="w-full px-3 py-2 text-sm bg-secondary border border-border rounded-lg focus:outline-none focus:border-primary transition-colors"
              />
            </div>
          </div>

          <!-- Text input (no options) -->
          <div v-else>
            <textarea
              v-model="answers[`question_${index}`]"
              rows="3"
              placeholder="请输入您的答案..."
              class="w-full px-3 py-2 text-sm bg-secondary border border-border rounded-lg focus:outline-none focus:border-primary transition-colors resize-none"
            />
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="sticky bottom-0 bg-background border-t border-border px-6 py-4">
        <div class="flex items-center justify-end gap-3">
          <button
            @click="handleClose"
            class="px-4 py-2 text-sm rounded-lg border border-border hover:bg-secondary transition-colors"
          >
            取消
          </button>
          <button
            @click="handleSubmit"
            :disabled="!isValid"
            class="px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            提交答案
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { HelpCircle, X } from 'lucide-vue-next';
import type { Question, UserAnswers } from '@/composables/useUserQuestion';

const props = defineProps<{
  show: boolean;
  questions: Question[];
}>();

const emit = defineEmits<{
  submit: [answers: UserAnswers];
  close: [];
}>();

// 答案状态
const answers = ref<UserAnswers>({});
const showOtherInput = ref<Record<number, boolean>>({});
const otherInputs = ref<Record<number, string>>({});

// 重置答案（当问题变化时）
watch(() => props.questions, () => {
  answers.value = {};
  showOtherInput.value = {};
  otherInputs.value = {};

  // 初始化多选题的答案为空数组
  props.questions.forEach((q, index) => {
    if (q.multiSelect) {
      answers.value[`question_${index}`] = [];
    }
  });
}, { immediate: true });

// 合并 "其他" 输入
watch(otherInputs, (newInputs) => {
  Object.entries(newInputs).forEach(([index, value]) => {
    const idx = parseInt(index);
    const question = props.questions[idx];

    if (value && showOtherInput.value[idx]) {
      if (question?.multiSelect) {
        // 多选题：添加到数组
        const current = answers.value[`question_${idx}`] as string[] || [];
        if (!current.includes(value)) {
          answers.value[`question_${idx}`] = [...current, value];
        }
      } else {
        // 单选题：直接设置
        answers.value[`question_${idx}`] = value;
      }
    }
  });
}, { deep: true });

// 验证是否所有问题都已回答
const isValid = computed(() => {
  return props.questions.every((_, index) => {
    const answer = answers.value[`question_${index}`];
    if (Array.isArray(answer)) {
      return answer.length > 0;
    }
    return answer && String(answer).trim().length > 0;
  });
});

const handleSubmit = () => {
  if (!isValid.value) return;
  emit('submit', answers.value);
};

const handleClose = () => {
  emit('close');
};
</script>
