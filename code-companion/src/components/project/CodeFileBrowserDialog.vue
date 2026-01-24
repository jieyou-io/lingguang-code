<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div class="bg-background rounded-lg w-full max-w-4xl h-[80vh] m-4 flex flex-col">
      <div class="flex items-center justify-between px-4 py-3 border-b border-border">
        <div>
          <h2 class="text-lg font-semibold">代码文件浏览器</h2>
          <p class="text-xs text-muted-foreground">项目: {{ projectName }}</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="text-muted-foreground hover:text-foreground"
            @click="previewOpen = !previewOpen"
            title="切换预览"
          >
            <PanelLeftClose v-if="previewOpen" class="w-4 h-4" />
            <PanelLeft v-else class="w-4 h-4" />
          </button>
          <button class="text-muted-foreground hover:text-foreground" @click="close">×</button>
        </div>
      </div>

      <div class="flex-1 overflow-hidden grid" :class="previewOpen ? 'grid-cols-[1fr,2fr]' : 'grid-cols-1'">
        <div class="border-r border-border overflow-y-auto p-3">
          <FileTreeNode
            v-for="node in fileTree"
            :key="node.id"
            :node="node"
            :depth="0"
            :selected-id="selectedId"
            @select="handleSelect"
          />
          <div v-if="fileTree.length === 0" class="py-6 text-center text-sm text-muted-foreground">
            暂无可用文件
          </div>
        </div>

        <div v-if="previewOpen" class="overflow-y-auto p-4">
          <div v-if="selectedFile" class="space-y-3">
            <div class="flex items-center gap-2 text-xs text-muted-foreground">
              <component :is="fileIcon(selectedFile.extension)" class="w-4 h-4" />
              <span class="font-mono">{{ selectedFile.name }}</span>
            </div>
            <pre class="p-3 rounded-lg bg-secondary/50 border border-border text-xs overflow-x-auto">
              <code>{{ selectedContent || '暂无预览内容' }}</code>
            </pre>
            <div v-if="contentLoading" class="text-xs text-muted-foreground">加载中...</div>
            <div v-else-if="contentTruncated" class="text-xs text-muted-foreground">内容过长，已截断显示</div>
          </div>
          <div v-else class="text-muted-foreground text-sm">请选择一个文件查看预览</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, ref, watch } from 'vue';
import {
  File,
  Folder,
  FolderOpen,
  FileCode,
  FileJson,
  FileText,
  Image,
  Settings,
  ChevronRight,
  ChevronDown,
  PanelLeftClose,
  PanelLeft,
} from 'lucide-vue-next';
import { ProjectFileNode } from '@/types';
import { getProjectFileContent } from '@/lib/services/project-files';

const props = defineProps<{
  open: boolean;
  projectName: string;
  projectPath?: string;
  fileTree?: ProjectFileNode[];
}>();

const emit = defineEmits<{
  'update:open': [value: boolean];
}>();

const previewOpen = ref(true);
const selectedId = ref<string | null>(null);
const contentLoading = ref(false);
const contentTruncated = ref(false);
const contentCache = ref<Record<string, string>>({});
const truncatedCache = ref<Record<string, boolean>>({});

const fileTree = computed(() => props.fileTree ?? []);

const fileIcon = (extension?: string) => {
  switch (extension) {
    case 'tsx':
    case 'ts':
    case 'jsx':
    case 'js':
      return FileCode;
    case 'json':
      return FileJson;
    case 'css':
    case 'scss':
      return Settings;
    case 'md':
    case 'txt':
      return FileText;
    case 'png':
    case 'jpg':
    case 'ico':
    case 'svg':
      return Image;
    default:
      return File;
  }
};

const flattenFiles = (nodes: ProjectFileNode[]): ProjectFileNode[] => {
  const result: ProjectFileNode[] = [];
  const walk = (list: ProjectFileNode[]) => {
    list.forEach(node => {
      result.push(node);
      if (node.children) walk(node.children);
    });
  };
  walk(nodes);
  return result;
};

const allNodes = computed(() => flattenFiles(fileTree.value));
const selectedFile = computed(() => allNodes.value.find(node => node.id === selectedId.value && node.type === 'file'));
const selectedContent = computed(() => {
  const file = selectedFile.value;
  if (!file?.path) return '';
  if (file.content) return file.content;
  return contentCache.value[file.path] || '';
});

const handleSelect = (node: ProjectFileNode) => {
  if (node.type === 'file') {
    selectedId.value = node.id;
  }
};

const close = () => emit('update:open', false);

const FileTreeNode = defineComponent({
  name: 'FileTreeNode',
  props: {
    node: { type: Object as () => ProjectFileNode, required: true },
    depth: { type: Number, default: 0 },
    selectedId: { type: String, default: null },
  },
  emits: ['select'],
  setup(localProps, { emit }) {
    const expanded = ref(localProps.depth < 2);
    const icon = computed(() => {
      if (localProps.node.type === 'folder') {
        return expanded.value ? FolderOpen : Folder;
      }
      return fileIcon(localProps.node.extension);
    });

    const handleClick = () => {
      if (localProps.node.type === 'folder') {
        expanded.value = !expanded.value;
      } else {
        emit('select', localProps.node);
      }
    };

    return () => {
      const isSelected = localProps.node.id === localProps.selectedId;
      const paddingLeft = `${localProps.depth * 12 + 8}px`;
      const caret =
        localProps.node.type === 'folder'
          ? h(expanded.value ? ChevronDown : ChevronRight, {
              class: 'w-3.5 h-3.5 text-muted-foreground',
            })
          : h('span');

      const iconNode = h(icon.value, {
        class: [
          'w-4 h-4',
          localProps.node.type === 'folder' ? 'text-primary' : 'text-muted-foreground',
        ],
      });

      const label = h('span', { class: 'text-sm truncate' }, localProps.node.name);

      const button = h(
        'button',
        {
          onClick: handleClick,
          class: [
            'w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition-colors',
            isSelected ? 'bg-primary/10 text-primary' : 'hover:bg-muted',
          ],
          style: { paddingLeft },
        },
        [caret, iconNode, label]
      );

      const children =
        localProps.node.type === 'folder' && expanded.value && localProps.node.children
          ? h(
              'div',
              localProps.node.children.map((child) =>
                h(FileTreeNode, {
                  key: child.id,
                  node: child,
                  depth: localProps.depth + 1,
                  selectedId: localProps.selectedId,
                  onSelect: (node: ProjectFileNode) => emit('select', node),
                })
              )
            )
          : null;

      return h('div', [button, children]);
    };
  },
});

watch(
  () => selectedFile.value,
  async (file) => {
    if (!file?.path || !props.projectPath) {
      contentTruncated.value = false;
      return;
    }
    if (file.content) {
      contentTruncated.value = false;
      return;
    }
    if (contentCache.value[file.path]) {
      contentTruncated.value = truncatedCache.value[file.path] || false;
      return;
    }

    contentLoading.value = true;
    contentTruncated.value = false;
    try {
      const response = await getProjectFileContent(props.projectPath, file.path);
      contentCache.value = { ...contentCache.value, [file.path]: response.content };
      truncatedCache.value = { ...truncatedCache.value, [file.path]: response.truncated };
      contentTruncated.value = response.truncated;
    } catch (error) {
      console.error('Failed to load file content:', error);
    } finally {
      contentLoading.value = false;
    }
  }
);

watch(
  () => props.projectPath,
  () => {
    selectedId.value = null;
    contentCache.value = {};
    truncatedCache.value = {};
    contentTruncated.value = false;
  }
);
</script>
