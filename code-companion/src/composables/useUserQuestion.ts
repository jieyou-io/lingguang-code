/**
 * 用户问答状态管理 Composable
 *
 * 管理 AskUserQuestion 工具的交互式问答流程
 * 当检测到 AskUserQuestion 工具调用时触发对话框
 */

import { ref, computed } from 'vue';

/**
 * 问题选项接口
 */
export interface QuestionOption {
  label: string;
  description?: string;
}

/**
 * 问题接口
 */
export interface Question {
  question: string;
  header?: string;
  options?: QuestionOption[];
  multiSelect?: boolean;
}

/**
 * 待回答的问题
 */
export interface PendingQuestion {
  /** 问题列表 */
  questions: Question[];
  /** 问题 ID（用于追踪） */
  questionId: string;
  /** 时间戳 */
  timestamp: number;
}

/**
 * 用户选择的答案
 */
export type UserAnswers = Record<string, string | string[]>;

/**
 * 生成问题的唯一 ID（基于问题内容的简单 hash）
 */
function generateQuestionId(questions: Question[]): string {
  const content = questions.map(q => q.question).join('|');
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    const char = content.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return `question_${Math.abs(hash)}_${questions.length}`;
}

/**
 * 从 sessionStorage 加载已回答问题 ID 集合
 */
function loadAnsweredQuestionIds(): Set<string> {
  try {
    const stored = sessionStorage.getItem('answered_question_ids');
    if (stored) {
      return new Set(JSON.parse(stored));
    }
  } catch (error) {
    console.warn('[UserQuestion] Failed to load answered question IDs:', error);
  }
  return new Set();
}

/**
 * 保存已回答问题 ID 集合到 sessionStorage
 */
function saveAnsweredQuestionIds(ids: Set<string>): void {
  try {
    sessionStorage.setItem('answered_question_ids', JSON.stringify(Array.from(ids)));
  } catch (error) {
    console.warn('[UserQuestion] Failed to save answered question IDs:', error);
  }
}

// 全局状态（单例模式）
const pendingQuestion = ref<PendingQuestion | null>(null);
const showQuestionDialog = ref(false);
const answeredQuestionIds = ref<Set<string>>(loadAnsweredQuestionIds());
let sendMessageCallback: ((message: string) => void) | null = null;

export function useUserQuestion() {
  /**
   * 检查问题是否已回答
   */
  const isQuestionAnswered = (questionId: string): boolean => {
    return answeredQuestionIds.value.has(questionId);
  };

  /**
   * 触发问答对话框
   */
  const triggerQuestionDialog = (questions: Question[]) => {
    const questionId = generateQuestionId(questions);

    // 如果问题已回答，不再弹窗
    if (isQuestionAnswered(questionId)) {
      console.log('[UserQuestion] Question already answered:', questionId);
      return;
    }

    console.log('[UserQuestion] Triggering question dialog:', questionId);
    pendingQuestion.value = {
      questions,
      questionId,
      timestamp: Date.now(),
    };
    showQuestionDialog.value = true;
  };

  /**
   * 提交答案 - 格式化并发送给 Claude
   */
  const submitAnswers = (answers: UserAnswers) => {
    if (!pendingQuestion.value) return;

    console.log('[UserQuestion] Submitting answers:', answers);

    // 格式化答案为发送给 Claude 的消息
    const formattedMessage = formatAnswersMessage(pendingQuestion.value.questions, answers);

    // 标记问题为已回答
    const newAnsweredIds = new Set(answeredQuestionIds.value);
    newAnsweredIds.add(pendingQuestion.value.questionId);
    answeredQuestionIds.value = newAnsweredIds;
    saveAnsweredQuestionIds(newAnsweredIds);

    // 关闭对话框
    closeQuestionDialog();

    // 发送答案给 Claude
    if (sendMessageCallback) {
      sendMessageCallback(formattedMessage);
    } else {
      console.warn('[UserQuestion] No send message callback set');
    }
  };

  /**
   * 关闭问答对话框
   */
  const closeQuestionDialog = () => {
    showQuestionDialog.value = false;
    pendingQuestion.value = null;
  };

  /**
   * 设置发送消息的回调
   */
  const setSendMessageCallback = (callback: ((message: string) => void) | null) => {
    sendMessageCallback = callback;
  };

  /**
   * 格式化答案为消息
   */
  const formatAnswersMessage = (questions: Question[], answers: UserAnswers): string => {
    const lines: string[] = [];

    questions.forEach((q, index) => {
      const questionKey = `question_${index}`;
      const answer = answers[questionKey];

      if (answer) {
        lines.push(`**${q.header || q.question}**`);
        if (Array.isArray(answer)) {
          lines.push(answer.map(a => `- ${a}`).join('\n'));
        } else {
          lines.push(answer);
        }
        lines.push('');
      }
    });

    return lines.join('\n');
  };

  return {
    pendingQuestion: computed(() => pendingQuestion.value),
    showQuestionDialog: computed(() => showQuestionDialog.value),
    answeredQuestionIds: computed(() => answeredQuestionIds.value),
    triggerQuestionDialog,
    submitAnswers,
    closeQuestionDialog,
    isQuestionAnswered,
    setSendMessageCallback,
  };
}
