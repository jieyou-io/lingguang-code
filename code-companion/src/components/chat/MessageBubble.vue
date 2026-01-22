<template>
  <div :class="['flex w-full mb-2 animate-slide-up', isUser ? 'justify-end' : 'justify-start']">
    <div v-if="isUser" class="flex flex-col items-end max-w-[85%] sm:max-w-[70%]">
      <div
        :class="[
          'rounded-[20px] px-5 py-2.5',
          'bg-secondary text-secondary-foreground',
          'border border-border/50 shadow-sm',
          'break-words text-[15px] leading-relaxed'
        ]"
      >
        <div class="whitespace-pre-wrap">
          {{ message.content }}
          <span
            v-if="message.isStreaming"
            class="inline-block w-2 h-4 ml-0.5 bg-primary animate-pulse rounded-sm"
          />
        </div>
      </div>
      <p v-if="message.tokens && !message.isStreaming" class="text-[10px] text-muted-foreground mt-1">
        {{ message.tokens }} tokens
      </p>
    </div>

    <div v-else class="flex flex-col w-full max-w-full overflow-hidden">
      <div class="w-full pr-4 overflow-hidden">
        <div
          v-if="message.content || message.isStreaming"
          :class="[
            'markdown-content text-[15px] leading-relaxed',
            'prose prose-sm dark:prose-invert max-w-none',
            'prose-p:leading-relaxed prose-p:my-2',
            'prose-headings:font-semibold prose-headings:tracking-tight',
            'prose-a:text-primary prose-a:no-underline hover:prose-a:underline',
            'prose-code:text-sm prose-code:bg-muted/50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded',
            'prose-pre:bg-transparent prose-pre:p-0 prose-pre:m-0',
            'prose-blockquote:border-l-4 prose-blockquote:border-primary/20 prose-blockquote:pl-4',
            'prose-ul:list-disc prose-ul:pl-6',
            'prose-ol:list-decimal prose-ol:pl-6',
            'prose-li:my-1',
            'prose-table:border-collapse prose-table:w-full',
            'prose-th:border prose-th:border-border prose-th:bg-muted/50 prose-th:px-4 prose-th:py-2',
            'prose-td:border prose-td:border-border prose-td:px-4 prose-td:py-2'
          ]"
          v-html="renderedContent"
        />
        <span
          v-if="message.isStreaming"
          class="inline-block w-2 h-4 ml-0.5 bg-primary animate-pulse rounded-sm"
        />

        <!-- 🔥 工具调用交互区域 -->
        <template v-if="message.toolUseBlocks && message.toolUseBlocks.length > 0">
          <template v-for="block in message.toolUseBlocks" :key="block.id">
            <!-- AskUserQuestion 卡片 -->
            <AskUserQuestionCard
              v-if="block.name === 'AskUserQuestion'"
              :tool-id="block.id"
              :questions="block.input?.questions || []"
              @submit="(answers) => handleQuestionSubmit(block.id, answers)"
            />
          </template>
        </template>

        <p v-if="message.tokens && !message.isStreaming" class="text-[10px] text-muted-foreground mt-1">
          {{ message.tokens }} tokens
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Message } from '@/types';
import { renderMarkdown } from '@/utils/markdown';
import AskUserQuestionCard from './AskUserQuestionCard.vue';

const props = defineProps<{ message: Message }>();

const emit = defineEmits<{
  permissionRespond: [toolId: string, response: 'y' | 'n'];
  questionSubmit: [toolId: string, answers: Record<string, any>];
}>();

const isUser = computed(() => props.message.role === 'user');

/**
 * 判断是否是需要权限的工具
 */
const isPermissionTool = (toolName: string): boolean => {
  const permissionTools = ['Write', 'Edit', 'Bash', 'NotebookEdit', 'KillShell'];
  return permissionTools.includes(toolName);
};

/**
 * 渲染 markdown 内容为 HTML
 */
const renderedContent = computed(() => {
  if (!props.message.content) return '';

  try {
    return renderMarkdown(props.message.content);
  } catch (error) {
    console.error('Markdown rendering error:', error);
    // 渲染失败时返回纯文本
    return `<pre class="whitespace-pre-wrap">${props.message.content}</pre>`;
  }
});

const handlePermissionRespond = (response: 'y' | 'n') => {
  const block = props.message.toolUseBlocks?.find(b => isPermissionTool(b.name));
  if (block) {
    emit('permissionRespond', block.id, response);
  }
};

const handleQuestionSubmit = (toolId: string, answers: Record<string, any>) => {
  emit('questionSubmit', toolId, answers);
};
</script>
