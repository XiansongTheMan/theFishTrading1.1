<!-- 连接测试：可切换 test_token / chat 两种测试模式 -->
<script setup lang="ts">
import { ref, computed, watch } from "vue";
import axios from "axios";
import { ElCard, ElButton, ElInput, ElScrollbar, ElIcon, ElMessage, ElSelect, ElOption } from "element-plus";
import { Loading } from "@element-plus/icons-vue";
import { agentChatTest, listAgentTemplates } from "../../api/grok";
import { testToken } from "../../api/config";
import RequestResponseLog from "./RequestResponseLog.vue";

const props = defineProps<{ agent: "grok" | "qwen" }>();

type TestMode = "connection" | "chat";
const testMode = ref<TestMode>("connection");
const currentModel = ref("");

const modeOptions = [
  { value: "connection" as TestMode, label: "连接测试" },
  { value: "chat" as TestMode, label: "chat测试" },
];

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  loading?: boolean;
}
const testInput = ref("");
const chatMessages = ref<ChatMsg[]>([]);
const connectionLoading = ref(false);
const connectionResult = ref<{ ok: boolean; message: string } | null>(null);
const lastRequest = ref<{ agent: string; content: string; messages?: Array<{ role: string; content: string }> } | null>(null);
const lastResponse = ref<{ ok: boolean; content: string } | null>(null);

const isChatMode = computed(() => testMode.value === "chat");

/** 进入 chat 模式时获取当前 Agent 选中的模型（来自 Agent 角色设定） */
async function fetchCurrentModel() {
  try {
    const res = (await listAgentTemplates(props.agent)) as { data?: { selected_model?: string } };
    currentModel.value = res?.data?.selected_model ?? "";
  } catch {
    currentModel.value = "";
  }
}

watch([() => props.agent, testMode], () => {
  if (testMode.value === "chat") fetchCurrentModel();
}, { immediate: true });

function getFullErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data;
    if (data?.detail) return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    if (data?.message) return data.message;
    if (err.response?.status) return "HTTP " + err.response.status + ": " + (err.message || "请求失败");
    if (err.code === "ECONNABORTED") return "请求超时（15 秒）";
    if (err.message) return err.message;
  }
  if (err instanceof Error && err.message) return err.message;
  return String(err) || "请求失败";
}

function clearChat() {
  chatMessages.value = [];
}

/** 连接测试：调用 test_token 验证 API Key 是否有效 */
async function runConnectionTest() {
  connectionLoading.value = true;
  connectionResult.value = null;
  try {
    const res = (await testToken(props.agent)) as { data?: { ok?: boolean; message?: string } };
    const ok = res?.data?.ok ?? false;
    const message = res?.data?.message ?? (ok ? "连接成功" : "连接失败");
    connectionResult.value = { ok, message };
    if (ok) ElMessage.success("连接测试成功");
    else ElMessage.warning(message);
  } catch (e) {
    const msg = getFullErrorMessage(e);
    connectionResult.value = { ok: false, message: msg };
    ElMessage.error("连接测试失败");
  } finally {
    connectionLoading.value = false;
  }
}

/** 输入框按键：Enter 发送，Shift+Enter 换行 */
function onInputKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    runChatTest();
  }
}

/** chat 测试：调用 chat 函数进行多轮对话 */
async function runChatTest() {
  const content = (testInput.value || "").trim() || "你好";
  testInput.value = "";
  chatMessages.value.push({ role: "user", content });
  const loadingIdx = chatMessages.value.length;
  chatMessages.value.push({ role: "assistant", content: "", loading: true });
  const history = chatMessages.value
    .slice(0, -2)
    .filter((m) => !m.loading && m.content)
    .map((m) => ({ role: m.role, content: m.content }));
  lastRequest.value = { agent: props.agent, content, messages: history.length > 0 ? history : undefined };
  try {
    const res = await agentChatTest(props.agent, content, history.length > 0 ? history : undefined);
    const ok = res?.data?.ok ?? false;
    const reply = res?.data?.content ?? (ok ? "" : "无返回");
    const modelUsed = (res?.data as { model?: string })?.model ?? "";
    if (modelUsed) currentModel.value = modelUsed;
    lastResponse.value = { ok, content: reply };
    chatMessages.value[loadingIdx] = { role: "assistant", content: reply };
    if (!ok && reply) ElMessage.warning(reply);
    else if (ok) ElMessage.success("测试成功");
  } catch (e) {
    const fullMsg = getFullErrorMessage(e);
    lastResponse.value = { ok: false, content: fullMsg };
    chatMessages.value[loadingIdx] = { role: "assistant", content: "请求失败\n\n" + fullMsg };
    ElMessage.error("测试失败");
  }
}
</script>

<template>
  <ElCard shadow="never" class="test-card">
    <template #header>
      <div class="test-header">
        <span>连接测试</span>
        <div class="test-header-actions">
          <ElSelect v-model="testMode" size="small" style="width: 120px" placeholder="选择测试模式">
            <ElOption v-for="opt in modeOptions" :key="opt.value" :value="opt.value" :label="opt.label" />
          </ElSelect>
          <ElButton v-if="isChatMode && chatMessages.length > 0" size="small" link type="info" @click="clearChat">清空对话</ElButton>
        </div>
      </div>
    </template>
    <p class="test-tip">
      {{ isChatMode ? "与当前选择的 Agent 进行测试对话，同一会话内带完整对话历史。不保存到数据库，刷新页面即清空。" : "验证 API Key 是否有效，发送极简请求测试连接。" }}
      <span v-if="isChatMode && currentModel" class="current-model">当前模型：{{ currentModel }}</span>
    </p>

    <!-- 连接测试：test_token -->
    <div v-if="!isChatMode" class="connection-test-area">
      <ElButton type="primary" :loading="connectionLoading" @click="runConnectionTest">测试连接</ElButton>
      <div v-if="connectionResult" :class="['connection-result', connectionResult.ok ? 'success' : 'error']">
        {{ connectionResult.ok ? "✓ " + connectionResult.message : "✗ " + connectionResult.message }}
      </div>
    </div>

    <!-- chat 测试：chat 函数 -->
    <div v-else class="chat-container">
      <ElScrollbar class="chat-messages" max-height="360px">
        <div v-if="chatMessages.length === 0" class="chat-empty">发送消息开始测试</div>
        <div v-for="(msg, idx) in chatMessages" :key="idx" :class="['chat-row', msg.role === 'user' ? 'chat-row-user' : 'chat-row-assistant']">
          <div :class="['chat-bubble', msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant']">
            <template v-if="msg.loading">
              <ElIcon class="chat-loading-icon" :size="16"><Loading /></ElIcon>
              <span>加载中</span>
            </template>
            <template v-else>{{ msg.content || "—" }}</template>
          </div>
        </div>
      </ElScrollbar>
      <div class="chat-input-row">
        <ElInput v-model="testInput" type="textarea" :rows="2" placeholder="输入测试内容。按下回车键发送，Shift+回车键换行" :disabled="chatMessages.some(m => m.loading)" @keydown="onInputKeydown" />
        <ElButton type="primary" :disabled="chatMessages.some(m => m.loading)" @click="runChatTest" class="chat-send-btn">发送</ElButton>
      </div>
    </div>
    <RequestResponseLog v-if="isChatMode" :request="lastRequest" :response="lastResponse" />
  </ElCard>
</template>

<style scoped>
.test-card { margin-bottom: 20px; }
.test-header { display: flex; justify-content: space-between; align-items: center; }
.test-header-actions { display: flex; align-items: center; gap: 8px; }
.connection-test-area { display: flex; flex-direction: column; gap: 12px; margin-bottom: 12px; }
.connection-result { padding: 10px 14px; border-radius: 8px; font-size: 0.95rem; }
.connection-result.success { background: var(--el-color-success-light-9); color: var(--el-color-success); }
.connection-result.error { background: var(--el-color-danger-light-9); color: var(--el-color-danger); }
.test-header-actions { display: flex; align-items: center; gap: 8px; }
.connection-test-area { display: flex; flex-direction: column; gap: 12px; }
.connection-result { padding: 10px 14px; border-radius: 8px; font-size: 0.9rem; }
.connection-result.success { background: var(--el-color-success-light-9); color: var(--el-color-success); }
.connection-result.error { background: var(--el-color-danger-light-9); color: var(--el-color-danger); }
.test-header-actions { display: flex; align-items: center; gap: 8px; }
.connection-test-area { display: flex; flex-direction: column; gap: 12px; margin-bottom: 12px; }
.connection-result { padding: 10px 14px; border-radius: 8px; font-size: 0.9rem; }
.connection-result.success { background: var(--el-color-success-light-9); color: var(--el-color-success-dark-2); }
.connection-result.error { background: var(--el-color-danger-light-9); color: var(--el-color-danger-dark-2); }
.test-header-actions { display: flex; align-items: center; gap: 8px; }
.connection-test-area { display: flex; flex-direction: column; gap: 12px; }
.connection-result { padding: 10px 14px; border-radius: 8px; font-size: 0.9rem; }
.connection-result.success { background: var(--el-color-success-light-9); color: var(--el-color-success); }
.connection-result.error { background: var(--el-color-danger-light-9); color: var(--el-color-danger); }
.test-header-actions { display: flex; align-items: center; gap: 8px; }
.connection-test-area { display: flex; flex-direction: column; gap: 12px; padding: 8px 0; }
.connection-result { padding: 10px 14px; border-radius: 8px; font-size: 0.9rem; }
.connection-result.success { background: var(--el-color-success-light-9); color: var(--el-color-success-dark-2); }
.connection-result.error { background: var(--el-color-danger-light-9); color: var(--el-color-danger-dark-2); }
.test-header-actions { display: flex; align-items: center; gap: 8px; }
.connection-test-area { display: flex; flex-direction: column; gap: 12px; }
.connection-result { padding: 10px 14px; border-radius: 8px; font-size: 0.95rem; }
.connection-result.success { background: var(--el-color-success-light-9); color: var(--el-color-success-dark-2); }
.connection-result.error { background: var(--el-color-danger-light-9); color: var(--el-color-danger-dark-2); }
.test-header-actions { display: flex; align-items: center; gap: 8px; }
.connection-test-area { display: flex; flex-direction: column; gap: 12px; }
.connection-result { padding: 10px 14px; border-radius: 8px; font-size: 0.9rem; }
.connection-result.success { background: var(--el-color-success-light-9); color: var(--el-color-success-dark-2); }
.connection-result.error { background: var(--el-color-danger-light-9); color: var(--el-color-danger-dark-2); }
.test-header-actions { display: flex; align-items: center; gap: 8px; }
.connection-test-area { display: flex; flex-direction: column; gap: 12px; }
.connection-result { padding: 10px 14px; border-radius: 8px; font-size: 0.9rem; }
.connection-result.success { background: var(--el-color-success-light-9); color: var(--el-color-success-dark-2); }
.connection-result.error { background: var(--el-color-danger-light-9); color: var(--el-color-danger-dark-2); }
.dark .connection-result.success { background: var(--el-color-success-dark-2); color: var(--el-color-success-light-3); }
.dark .connection-result.error { background: var(--el-color-danger-dark-2); color: var(--el-color-danger-light-3); }
.test-header-actions { display: flex; align-items: center; gap: 12px; }
.test-tip { font-size: 0.85rem; color: var(--el-text-color-secondary); margin: 0 0 12px; }
.current-model { margin-left: 8px; font-weight: 500; color: var(--el-color-primary); }
.current-model { margin-left: 12px; font-weight: 500; color: var(--el-color-primary); }
.current-model { margin-left: 8px; color: var(--el-color-primary); font-weight: 500; }
.connection-test-area { display: flex; flex-direction: column; gap: 12px; padding: 8px 0; }
.connection-result { font-size: 0.9rem; padding: 10px 14px; border-radius: 8px; }
.connection-result.success { background: var(--el-color-success-light-9); color: var(--el-color-success-dark-2); }
.connection-result.error { background: var(--el-color-danger-light-9); color: var(--el-color-danger-dark-2); }
.dark .connection-result.success { background: var(--el-color-success-dark-2); color: var(--el-color-success-light-9); }
.dark .connection-result.error { background: var(--el-color-danger-dark-2); color: var(--el-color-danger-light-9); }
.chat-container { display: flex; flex-direction: column; gap: 12px; }
.chat-messages { padding: 8px 0; }
.chat-empty { text-align: center; color: var(--el-text-color-placeholder); font-size: 0.9rem; padding: 24px; }
.chat-row { display: flex; margin-bottom: 12px; }
.chat-row-user { justify-content: flex-end; }
.chat-row-assistant { justify-content: flex-start; }
.chat-bubble { max-width: 78%; padding: 10px 14px; border-radius: 12px; font-size: 0.95rem; line-height: 1.5; word-break: break-word; white-space: pre-wrap; }
.chat-bubble-user { background: var(--el-color-primary); color: #fff; border-top-right-radius: 4px; }
.chat-bubble-assistant { background: var(--el-fill-color-light); color: var(--el-text-color-primary); border-top-left-radius: 4px; }
.dark .chat-bubble-assistant { background: var(--el-fill-color); }
.chat-loading-icon { margin-right: 6px; vertical-align: middle; animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.chat-input-row { display: flex; gap: 8px; align-items: flex-end; }
.chat-input-row :deep(.el-input) { flex: 1; }
.chat-send-btn { flex-shrink: 0; }
</style>
