<template>
  <div v-if="open" class="fixed inset-0 z-50">
    <div class="absolute inset-0 bg-black/40" @click="close" />
    <div class="absolute right-0 top-0 h-full w-full sm:max-w-md bg-background border-l border-border shadow-lg p-4">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">管理文件</h2>
        <button class="text-muted-foreground hover:text-foreground" @click="close">×</button>
      </div>

      <div class="mt-4 space-y-4">
        <div class="flex items-center justify-between text-sm">
          <span class="text-muted-foreground">已添加 {{ fileContextItems.length }} 个文件</span>
          <span class="text-primary">{{ totalFileTokens.toLocaleString() }} tokens</span>
        </div>

        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            v-model="searchQuery"
            class="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-background text-sm"
            placeholder="搜索文件..."
          />
        </div>

        <div class="h-[calc(100vh-220px)] overflow-y-auto">
          <div class="space-y-0.5">
            <FileTreeNode
              v-for="file in mockFileTree"
              :key="file.id"
              :file="file"
              :context-items="contextItems"
              :search-query="searchQuery"
              :depth="0"
              @add-file="onAddFile"
              @remove-file="onRemoveFile"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, ref } from 'vue';
import {
  Search,
  Folder,
  FileCode,
  FileText,
  FileJson,
  Plus,
  Check,
  ChevronRight,
  ChevronDown,
} from 'lucide-vue-next';
import { ContextItem } from '@/types';

interface MockFile {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'folder';
  children?: MockFile[];
  tokens?: number;
  extension?: string;
}

const props = defineProps<{
  open: boolean;
  onOpenChange: (open: boolean) => void;
  contextItems: ContextItem[];
  onAddFile: (file: MockFile) => void;
  onRemoveFile: (fileId: string) => void;
}>();

const searchQuery = ref('');

const mockFileTree: MockFile[] = [
  {
    id: 'src',
    name: 'src',
    path: '/src',
    type: 'folder',
    children: [
      {
        id: 'components',
        name: 'components',
        path: '/src/components',
        type: 'folder',
        children: [
          { id: 'Header.vue', name: 'Header.vue', path: '/src/components/Header.vue', type: 'file', tokens: 850, extension: 'vue' },
          { id: 'Sidebar.vue', name: 'Sidebar.vue', path: '/src/components/Sidebar.vue', type: 'file', tokens: 1200, extension: 'vue' },
          { id: 'ChatInput.vue', name: 'ChatInput.vue', path: '/src/components/ChatInput.vue', type: 'file', tokens: 650, extension: 'vue' },
        ],
      },
      {
        id: 'pages',
        name: 'pages',
        path: '/src/pages',
        type: 'folder',
        children: [
          { id: 'Index.vue', name: 'Index.vue', path: '/src/pages/Index.vue', type: 'file', tokens: 1500, extension: 'vue' },
          { id: 'Settings.vue', name: 'Settings.vue', path: '/src/pages/Settings.vue', type: 'file', tokens: 980, extension: 'vue' },
        ],
      },
      { id: 'App.vue', name: 'App.vue', path: '/src/App.vue', type: 'file', tokens: 450, extension: 'vue' },
      { id: 'main.ts', name: 'main.ts', path: '/src/main.ts', type: 'file', tokens: 120, extension: 'ts' },
    ],
  },
  {
    id: 'public',
    name: 'public',
    path: '/public',
    type: 'folder',
    children: [
      { id: 'index.html', name: 'index.html', path: '/public/index.html', type: 'file', tokens: 80, extension: 'html' },
    ],
  },
  { id: 'package.json', name: 'package.json', path: '/package.json', type: 'file', tokens: 200, extension: 'json' },
  { id: 'README.md', name: 'README.md', path: '/README.md', type: 'file', tokens: 350, extension: 'md' },
];

const fileIcons: Record<string, any> = {
  tsx: FileCode,
  ts: FileCode,
  jsx: FileCode,
  js: FileCode,
  json: FileJson,
  md: FileText,
  html: FileText,
  css: FileText,
};

const fileContextItems = computed(() => props.contextItems.filter(item => item.type === 'file'));
const totalFileTokens = computed(() => fileContextItems.value.reduce((sum, item) => sum + item.tokens, 0));

const close = () => props.onOpenChange(false);

const FileTreeNode = defineComponent({
  name: 'FileTreeNode',
  props: {
    file: { type: Object as () => MockFile, required: true },
    depth: { type: Number, default: 0 },
    contextItems: { type: Array as () => ContextItem[], required: true },
    searchQuery: { type: String, required: true },
  },
  emits: ['add-file', 'remove-file'],
  setup(localProps, { emit }) {
    const expanded = ref(localProps.depth < 2);

    const isInContext = computed(() =>
      localProps.contextItems.some(item => item.path === localProps.file.path)
    );

    const matchesSearch = computed(() =>
      localProps.searchQuery
        ? localProps.file.name.toLowerCase().includes(localProps.searchQuery.toLowerCase())
        : true
    );

    const hasMatchingChildren = computed(() => {
      if (!localProps.searchQuery || localProps.file.type !== 'folder') return false;
      const checkChildren = (children: MockFile[]): boolean => {
        return children.some(child =>
          child.name.toLowerCase().includes(localProps.searchQuery.toLowerCase()) ||
          (child.children && checkChildren(child.children))
        );
      };
      return localProps.file.children ? checkChildren(localProps.file.children) : false;
    });

    const Icon = computed(() =>
      localProps.file.type === 'folder'
        ? Folder
        : fileIcons[localProps.file.extension || ''] || FileText
    );

    const handleToggle = () => {
      if (localProps.file.type === 'file') {
        if (isInContext.value) {
          emit('remove-file', localProps.file.id);
        } else {
          emit('add-file', localProps.file);
        }
      } else {
        expanded.value = !expanded.value;
      }
    };

    return {
      expanded,
      isInContext,
      matchesSearch,
      hasMatchingChildren,
      Icon,
      handleToggle,
      ChevronDown,
      ChevronRight,
      Plus,
      Check,
    };
  },
  template: `
    <div>
      <button
        v-if="matchesSearch || hasMatchingChildren || file.type === 'folder'"
        @click="handleToggle"
        :class="[
          'w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition-colors',
          isInContext ? 'bg-primary/10 text-primary' : 'hover:bg-muted'
        ]"
        :style="{ paddingLeft: (depth * 12 + 8) + 'px' }"
      >
        <component
          :is="file.type === 'folder' ? (expanded ? ChevronDown : ChevronRight) : 'span'"
          class="w-3.5 h-3.5 text-muted-foreground"
        />

        <component :is="Icon" :class="['w-4 h-4', file.type === 'folder' ? 'text-primary' : 'text-muted-foreground']" />

        <span class="flex-1 text-sm truncate">{{ file.name }}</span>

        <template v-if="file.type === 'file'">
          <span class="text-[10px] text-muted-foreground">{{ file.tokens?.toLocaleString() }} tokens</span>
          <Check v-if="isInContext" class="w-4 h-4 text-primary" />
          <Plus v-else class="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100" />
        </template>
      </button>

      <div v-if="file.type === 'folder' && expanded && file.children">
        <FileTreeNode
          v-for="child in file.children"
          :key="child.id"
          :file="child"
          :depth="depth + 1"
          :context-items="contextItems"
          :search-query="searchQuery"
          @add-file="$emit('add-file', $event)"
          @remove-file="$emit('remove-file', $event)"
        />
      </div>
    </div>
  `,
});
</script>
