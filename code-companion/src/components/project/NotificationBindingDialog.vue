<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div class="bg-background rounded-lg p-6 max-w-[480px] w-full m-4">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-lg font-semibold flex items-center gap-2">
            <Bell class="w-5 h-5 text-primary" />
            绑定机器人通知
          </h2>
          <p class="text-sm text-muted-foreground mt-1">
            为项目 <span class="font-medium text-foreground">{{ projectName }}</span> 配置通知
          </p>
        </div>
        <button class="text-muted-foreground hover:text-foreground" @click="close">×</button>
      </div>

      <div class="space-y-6 py-2">
        <div class="space-y-2">
          <label class="flex items-center gap-2 text-sm">
            <Webhook class="w-4 h-4" />
            Webhook 地址
          </label>
          <div class="flex gap-2">
            <input
              v-model="webhookUrl"
              placeholder="https://your-webhook-url.com/notify"
              class="flex-1 px-3 py-2 rounded-md border border-border bg-background text-sm"
            />
            <button
              class="px-3 py-2 text-sm rounded-md border border-border hover:bg-muted"
              :disabled="isTesting || !webhookUrl"
              @click="handleTestWebhook"
            >
              {{ isTesting ? '测试中...' : '测试' }}
            </button>
          </div>
          <p class="text-xs text-muted-foreground">支持企业微信、钉钉、飞书等机器人 Webhook</p>
        </div>

        <div class="space-y-3">
          <label class="flex items-center gap-2 text-sm">
            <MessageSquare class="w-4 h-4" />
            通知规则
          </label>
          <div class="space-y-2">
            <div
              v-for="rule in rules"
              :key="rule.id"
              class="flex items-center justify-between p-3 rounded-lg bg-secondary/50 border border-border"
            >
              <div class="flex items-center gap-3">
                <div :class="['p-1.5 rounded-md', rule.enabled ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground']">
                  <component :is="rule.icon" class="w-4 h-4" />
                </div>
                <div>
                  <p class="text-sm font-medium">{{ rule.name }}</p>
                  <p class="text-xs text-muted-foreground">{{ rule.description }}</p>
                </div>
              </div>
              <input
                type="checkbox"
                class="accent-primary"
                :checked="rule.enabled"
                @change="() => handleRuleToggle(rule.id)"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 mt-6">
        <button class="px-3 py-2 text-sm rounded-md border border-border hover:bg-muted" @click="close">取消</button>
        <button
          class="px-3 py-2 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
          :disabled="isLoading"
          @click="handleSave"
        >
          {{ isLoading ? '保存中...' : '保存配置' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Bell, Webhook, MessageSquare, AlertTriangle, CheckCircle, XCircle } from 'lucide-vue-next';
import { useToast } from '@/composables/useToast';

interface NotificationRule {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  icon: any;
}

const props = defineProps<{
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectName: string;
  projectId: string;
}>();

const { toast } = useToast();
const webhookUrl = ref('');
const isLoading = ref(false);
const isTesting = ref(false);

const rules = ref<NotificationRule[]>([
  { id: 'session_complete', name: '会话完成', description: '当 AI 完成回复时通知', enabled: true, icon: CheckCircle },
  { id: 'session_error', name: '会话错误', description: '当会话出现错误时通知', enabled: true, icon: XCircle },
  { id: 'context_warning', name: '上下文警告', description: '当上下文使用超过 80% 时通知', enabled: false, icon: AlertTriangle },
  { id: 'daily_summary', name: '每日摘要', description: '每天发送使用统计摘要', enabled: false, icon: MessageSquare },
]);

const handleRuleToggle = (ruleId: string) => {
  rules.value = rules.value.map(rule =>
    rule.id === ruleId ? { ...rule, enabled: !rule.enabled } : rule
  );
};

const handleTestWebhook = async () => {
  if (!webhookUrl.value) {
    toast({ title: '请输入 Webhook 地址', description: '需要填写 Webhook URL 才能测试', variant: 'destructive' });
    return;
  }

  isTesting.value = true;
  try {
    await fetch(webhookUrl.value, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      mode: 'no-cors',
      body: JSON.stringify({
        type: 'test',
        project_id: props.projectId,
        project_name: props.projectName,
        timestamp: new Date().toISOString(),
        message: '这是一条测试通知',
      }),
    });

    toast({ title: '测试请求已发送', description: '请检查您的机器人是否收到消息' });
  } catch (error) {
    console.error('Webhook test failed:', error);
    toast({ title: '测试失败', description: '无法发送测试请求，请检查 Webhook 地址', variant: 'destructive' });
  } finally {
    isTesting.value = false;
  }
};

const handleSave = async () => {
  if (!webhookUrl.value) {
    toast({ title: '请输入 Webhook 地址', description: '需要填写 Webhook URL 才能保存', variant: 'destructive' });
    return;
  }

  isLoading.value = true;
  try {
    await new Promise(resolve => setTimeout(resolve, 500));
    const enabledRules = rules.value.filter(r => r.enabled);
    toast({ title: '绑定成功', description: `已启用 ${enabledRules.length} 条通知规则` });
    props.onOpenChange(false);
  } catch (error) {
    toast({ title: '保存失败', description: '请稍后重试', variant: 'destructive' });
  } finally {
    isLoading.value = false;
  }
};

const close = () => props.onOpenChange(false);
</script>
