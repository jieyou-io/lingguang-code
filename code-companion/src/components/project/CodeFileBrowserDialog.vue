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
            v-for="node in mockFileTree"
            :key="node.id"
            :node="node"
            :depth="0"
            :selected-id="selectedId"
            @select="handleSelect"
          />
        </div>

        <div v-if="previewOpen" class="overflow-y-auto p-4">
          <div v-if="selectedFile" class="space-y-3">
            <div class="flex items-center gap-2 text-xs text-muted-foreground">
              <component :is="fileIcon(selectedFile.extension)" class="w-4 h-4" />
              <span class="font-mono">{{ selectedFile.name }}</span>
            </div>
            <pre class="p-3 rounded-lg bg-secondary/50 border border-border text-xs overflow-x-auto">
              <code>{{ selectedFile.content || '暂无预览内容' }}</code>
            </pre>
          </div>
          <div v-else class="text-muted-foreground text-sm">请选择一个文件查看预览</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, ref } from 'vue';
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

interface FileNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  children?: FileNode[];
  content?: string;
  extension?: string;
}

const props = defineProps<{
  open: boolean;
  projectName: string;
}>();

const emit = defineEmits<{
  'update:open': [value: boolean];
}>();

const previewOpen = ref(true);
const selectedId = ref<string | null>(null);

const mockFileTree: FileNode[] = [
  {
    id: '1',
    name: 'src',
    type: 'folder',
    children: [
      {
        id: '1-1',
        name: 'components',
        type: 'folder',
        children: [
          {
            id: '1-1-1',
            name: 'Button.vue',
            type: 'file',
            extension: 'vue',
            content: `<template>\n  <button :class=\"['btn', variantClass]\" @click=\"$emit('click')\">\n    <slot />\n  </button>\n</template>\n\n<script setup lang=\"ts\">\nconst props = withDefaults(defineProps<{ variant?: 'primary' | 'secondary' }>(), {\n  variant: 'primary',\n});\n\nconst variantClass = props.variant === 'primary' ? 'btn-primary' : 'btn-secondary';\n<\\/script>`,
          },
          {
            id: '1-1-2',
            name: 'Header.vue',
            type: 'file',
            extension: 'vue',
            content: `<template>\n  <header class=\"header\">\n    <h1>My App</h1>\n    <nav>\n      <Button>Home</Button>\n      <Button variant=\"secondary\">About</Button>\n    </nav>\n  </header>\n</template>\n\n<script setup lang=\"ts\">\nimport Button from './Button.vue';\n<\\/script>`,
          },
        ],
      },
      {
        id: '1-2',
        name: 'hooks',
        type: 'folder',
        children: [
          {
            id: '1-2-1',
            name: 'useAuth.ts',
            type: 'file',
            extension: 'ts',
            content: `import { ref, onMounted } from 'vue';\n\nexport function useAuth() {\n  const user = ref(null);\n  const loading = ref(true);\n\n  onMounted(() => {\n    loading.value = false;\n  });\n\n  return { user, loading };\n}`,
          },
        ],
      },
      {
        id: '1-3',
        name: 'App.vue',
        type: 'file',
        extension: 'vue',
        content: `<template>\n  <div class=\"app\">\n    <Header />\n    <main>\n      <h2>Welcome to My App</h2>\n    </main>\n  </div>\n</template>\n\n<script setup lang=\"ts\">\nimport Header from './components/Header.vue';\n<\\/script>`,
      },
    ],
  },
  {
    id: '2',
    name: 'public',
    type: 'folder',
    children: [
      { id: '2-1', name: 'favicon.ico', type: 'file', extension: 'ico' },
      { id: '2-2', name: 'logo.png', type: 'file', extension: 'png' },
    ],
  },
  {
    id: '3',
    name: 'package.json',
    type: 'file',
    extension: 'json',
    content: `{
  "name": "my-app",
  "version": "1.0.0"
}`,
  },
  {
    id: '4',
    name: 'README.md',
    type: 'file',
    extension: 'md',
    content: `# My App\n\nA modern React application.\n`,
  },
];

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

const flattenFiles = (nodes: FileNode[]): FileNode[] => {
  const result: FileNode[] = [];
  const walk = (list: FileNode[]) => {
    list.forEach(node => {
      result.push(node);
      if (node.children) walk(node.children);
    });
  };
  walk(nodes);
  return result;
};

const allNodes = computed(() => flattenFiles(mockFileTree));
const selectedFile = computed(() => allNodes.value.find(node => node.id === selectedId.value && node.type === 'file'));

const handleSelect = (node: FileNode) => {
  if (node.type === 'file') {
    selectedId.value = node.id;
  }
};

const close = () => emit('update:open', false);

const FileTreeNode = defineComponent({
  name: 'FileTreeNode',
  props: {
    node: { type: Object as () => FileNode, required: true },
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

    return { expanded, icon, handleClick, ChevronDown, ChevronRight, fileIcon };
  },
  template: `
    <div>
      <button
        @click="handleClick"
        :class="[
          'w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition-colors',
          node.id === selectedId ? 'bg-primary/10 text-primary' : 'hover:bg-muted'
        ]"
        :style="{ paddingLeft: (depth * 12 + 8) + 'px' }"
      >
        <component
          :is="node.type === 'folder' ? (expanded ? ChevronDown : ChevronRight) : 'span'"
          class="w-3.5 h-3.5 text-muted-foreground"
        />
        <component :is="icon" :class="['w-4 h-4', node.type === 'folder' ? 'text-primary' : 'text-muted-foreground']" />
        <span class="text-sm truncate">{{ node.name }}</span>
      </button>
      <div v-if="node.type === 'folder' && expanded && node.children">
        <FileTreeNode
          v-for="child in node.children"
          :key="child.id"
          :node="child"
          :depth="depth + 1"
          :selected-id="selectedId"
          @select="$emit('select', $event)"
        />
      </div>
    </div>
  `,
});
</script>
