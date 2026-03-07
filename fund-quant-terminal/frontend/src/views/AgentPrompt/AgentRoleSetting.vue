<!-- Agent 角色设定：grok/qwen 可选，多模板，下拉选择/删除 -->
<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import MarkdownIt from "markdown-it";
import {
  ElCard,
  ElInput,
  ElButton,
  ElMessage,
  ElSelect,
  ElOption,
  ElEmpty,
  ElMessageBox,
  ElTooltip,
} from "element-plus";
import { Delete, Refresh } from "@element-plus/icons-vue";
import {
  listAgentTemplates,
  createAgentTemplate,
  updateAgentTemplate,
  deleteAgentTemplate,
  selectAgentTemplate,
  updateAgentModel,
  syncAgentModels,
  type AgentTemplateItem,
} from "../../api/grok";

/** 前端兜底模型列表，当 API 未返回或失败时使用，确保下拉框可操作 */
const FALLBACK_GROK_MODELS = [
  { value: "grok-4-fast-reasoning", label: "grok-4-fast-reasoning（推荐）" },
  { value: "grok-2-1212", label: "grok-2-1212" },
  { value: "grok-3", label: "grok-3" },
  { value: "grok-4-1-fast-non-reasoning", label: "grok-4-1-fast-non-reasoning" },
];
const FALLBACK_QWEN_MODELS = [
  { value: "qwen-turbo", label: "qwen-turbo（快速）" },
  { value: "qwen-turbo-latest", label: "qwen-turbo-latest" },
  { value: "qwen3.5-flash", label: "qwen3.5-flash（推荐）" },
  { value: "qwen-flash", label: "qwen-flash" },
  { value: "qwen-flash-latest", label: "qwen-flash-latest" },
  { value: "qwen-plus", label: "qwen-plus" },
  { value: "qwen-plus-latest", label: "qwen-plus-latest" },
  { value: "qwen3.5-plus", label: "qwen3.5-plus" },
  { value: "qwen-max", label: "qwen-max" },
  { value: "qwen-max-latest", label: "qwen-max-latest" },
  { value: "qwen-long", label: "qwen-long（长文本）" },
  { value: "qwen-long-latest", label: "qwen-long-latest" },
  { value: "qwen2.5-72b-instruct", label: "qwen2.5-72b-instruct" },
  { value: "qwen2.5-32b-instruct", label: "qwen2.5-32b-instruct" },
  { value: "qwen2.5-14b-instruct", label: "qwen2.5-14b-instruct" },
  { value: "qwen2.5-7b-instruct", label: "qwen2.5-7b-instruct" },
  { value: "qwen2.5-1.5b-instruct", label: "qwen2.5-1.5b-instruct" },
  { value: "qwen2-72b-instruct", label: "qwen2-72b-instruct" },
  { value: "qwen2-7b-instruct", label: "qwen2-7b-instruct" },
  { value: "qwen2-1.5b-instruct", label: "qwen2-1.5b-instruct" },
  { value: "qwen2.5-coder-32b-instruct", label: "qwen2.5-coder-32b（代码）" },
  { value: "qwen2.5-coder-7b-instruct", label: "qwen2.5-coder-7b（代码）" },
  { value: "qwen-vl-max", label: "qwen-vl-max（视觉）" },
  { value: "qwen-vl-plus", label: "qwen-vl-plus（视觉）" },
  { value: "qwen2-0.5b-instruct", label: "qwen2-0.5b-instruct" },
];

/** 模型说明映射，用于悬停 tooltip */
const MODEL_DESCRIPTIONS: Record<string, string> = {
  "qwen-turbo": "快速推理模型，适合简单对话与高并发场景",
  "qwen-turbo-latest": "qwen-turbo 最新版，持续更新",
  "qwen3.5-flash": "速度快、性价比高，推荐日常使用",
  "qwen-flash": "轻量快速模型，响应迅速",
  "qwen-flash-latest": "qwen-flash 最新版",
  "qwen-plus": "增强版，理解与生成能力更强",
  "qwen-plus-latest": "qwen-plus 最新版",
  "qwen3.5-plus": "增强版，综合能力出色",
  "qwen-max": "最强模型，适合复杂任务",
  "qwen-max-latest": "qwen-max 最新版",
  "qwen-long": "长文本模型，支持百万级上下文",
  "qwen-long-latest": "qwen-long 最新版",
  "qwen2.5-72b-instruct": "72B 参数，高精度对话",
  "qwen2.5-32b-instruct": "32B 参数，性能与成本平衡",
  "qwen2.5-14b-instruct": "14B 参数，轻量高效",
  "qwen2.5-7b-instruct": "7B 参数，快速推理",
  "qwen2.5-1.5b-instruct": "1.5B 参数，超轻量",
  "qwen2-72b-instruct": "Qwen2 72B 版本",
  "qwen2-7b-instruct": "Qwen2 7B 版本",
  "qwen2-1.5b-instruct": "Qwen2 1.5B 版本",
  "qwen2.5-coder-32b-instruct": "代码专用，32B 参数",
  "qwen2.5-coder-7b-instruct": "代码专用，7B 参数",
  "qwen-vl-max": "视觉语言模型，支持图像理解",
  "qwen-vl-plus": "视觉语言模型，轻量版",
  "qwen2-0.5b-instruct": "Qwen2 0.5B 超轻量版本",
  "grok-2-1212": "推荐，131K 上下文，综合能力强",
  "grok-3": "新一代模型，能力升级",
  "grok-3-mini": "轻量版，响应更快",
  "grok-4-1-fast-non-reasoning": "快速非推理模式",
};

function getModelDesc(value: string): string {
  return MODEL_DESCRIPTIONS[value] ?? `模型：${value}`;
}

const agent = defineModel<"grok" | "qwen">("agent", { default: "grok" });
const loading = ref(false);
const saving = ref(false);
const syncingModels = ref(false);
const templates = ref<AgentTemplateItem[]>([]);
const selectedId = ref("");
const selectedModel = ref("");
const models = ref<Array<{ value: string; label: string }>>([]);
const primaryAiAgent = ref<"grok" | "qwen">("grok");
const templateName = ref("");
const promptContent = ref("");

const currentTemplate = computed(() =>
  templates.value.find((t) => t.id === selectedId.value)
);

const md = new MarkdownIt({ html: false });
const previewHtml = computed(() => {
  const raw = promptContent.value || "";
  return raw ? md.render(raw) : "";
});

async function load(ag?: "grok" | "qwen") {
  const a = ag ?? agent.value;
  loading.value = true;
  try {
    const res = (await listAgentTemplates(a)) as {
      data?: {
        items?: AgentTemplateItem[];
        selected_id?: string;
        primary_ai_agent?: string;
        models?: Array<{ value: string; label: string }>;
        selected_model?: string;
      };
    };
    templates.value = res?.data?.items ?? [];
    selectedId.value = res?.data?.selected_id ?? "";
    models.value = res?.data?.models ?? [];
    if (models.value.length === 0 && a === "qwen") models.value = FALLBACK_QWEN_MODELS;
    if (models.value.length === 0 && a === "grok") models.value = FALLBACK_GROK_MODELS;
    selectedModel.value = res?.data?.selected_model ?? "";
    const defaultModel = a === "qwen" ? "qwen-max" : "grok-4-fast-reasoning";
    const hasDefault = models.value.some((m) => m.value === defaultModel);
    if (!hasDefault && models.value.length > 0) {
      models.value = [{ value: defaultModel, label: defaultModel }, ...models.value];
    }
    const inList = models.value.some((m) => m.value === selectedModel.value);
    if (!selectedModel.value || !inList) {
      selectedModel.value = models.value.find((m) => m.value === defaultModel)?.value ?? models.value[0]?.value ?? defaultModel;
    }
    const primary = (res?.data?.primary_ai_agent || "grok") === "qwen" ? "qwen" : "grok";
    primaryAiAgent.value = primary;
    if (!ag) {
      agent.value = primary;
      if (primary !== a) return load(primary);
    }
    if (templates.value.length > 0 && !selectedId.value) selectedId.value = templates.value[0].id;
    syncContentFromSelected();
  } catch {
    templates.value = [];
    selectedId.value = "";
    models.value = agent.value === "qwen" ? FALLBACK_QWEN_MODELS : FALLBACK_GROK_MODELS;
    ElMessage.error("加载失败");
  } finally {
    loading.value = false;
  }
}

function syncContentFromSelected() {
  const t = currentTemplate.value;
  templateName.value = t?.name ?? "";
  promptContent.value = t?.content ?? "";
}

async function onModelChange(val: string) {
  try {
    await updateAgentModel(agent.value, val || "");
    ElMessage.success("模型已保存");
  } catch {
    ElMessage.error("保存模型失败");
  }
}

async function syncModels() {
  syncingModels.value = true;
  try {
    const res = (await syncAgentModels(agent.value)) as {
      data?: { models?: Array<{ value: string; label: string }>; from_api?: boolean };
    };
    const list = res?.data?.models ?? [];
    if (list.length > 0) {
      models.value = list;
      ElMessage.success(res?.data?.from_api ? "已从官方接口同步模型列表" : "已加载模型列表");
    } else {
      models.value = agent.value === "qwen" ? FALLBACK_QWEN_MODELS : FALLBACK_GROK_MODELS;
      ElMessage.warning("同步无结果，已使用兜底列表");
    }
  } catch {
    models.value = agent.value === "qwen" ? FALLBACK_QWEN_MODELS : FALLBACK_GROK_MODELS;
    ElMessage.error("同步失败，已使用兜底列表");
  } finally {
    syncingModels.value = false;
  }
}

watch(selectedId, () => syncContentFromSelected());
watch(agent, (a) => load(a));

async function addNew() {
  const name = (templateName.value || promptContent.value || "未命名").trim().slice(0, 50) || "未命名";
  if (!promptContent.value.trim()) {
    ElMessage.warning("请输入角色设定内容");
    return;
  }
  saving.value = true;
  try {
    const res = (await createAgentTemplate({
      agent: agent.value,
      name,
      content: promptContent.value,
    })) as { data?: { id: string } };
    if (res?.data?.id) {
      ElMessage.success("已保存");
      await load();
      selectedId.value = res.data.id;
      syncContentFromSelected();
    }
  } catch {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
}

async function saveCurrent() {
  if (!selectedId.value) {
    addNew();
    return;
  }
  const name = (templateName.value || "未命名").trim() || "未命名";
  saving.value = true;
  try {
    await updateAgentTemplate(selectedId.value, { name, content: promptContent.value });
    ElMessage.success("已更新");
    await load();
    syncContentFromSelected();
  } catch {
    ElMessage.error("更新失败");
  } finally {
    saving.value = false;
  }
}

async function doSelect(id: string) {
  try {
    await selectAgentTemplate(id);
    selectedId.value = id;
    ElMessage.success("已选中");
    await load();
  } catch {
    ElMessage.error("选中失败");
  }
}

async function doDelete(id: string) {
  try {
    await ElMessageBox.confirm("确定删除该角色设定？", "确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await deleteAgentTemplate(id);
    ElMessage.success("已删除");
    if (selectedId.value === id) selectedId.value = templates.value.find((t) => t.id !== id)?.id ?? "";
    await load();
  } catch {
    ElMessage.error("删除失败");
  }
}

onMounted(() => load());
</script>

<template>
  <div class="agent-role-setting">
    <ElCard shadow="never" class="main-card">
      <template #header>
        <span>Agent 角色设定</span>
        <div class="header-actions">
          <ElSelect v-model="agent" size="small" style="width: 140px" @change="load">
            <ElOption label="Grok (x.ai)" value="grok" />
            <ElOption label="通义千问 (Qwen)" value="qwen" />
          </ElSelect>
          <ElSelect
            v-model="selectedModel"
            placeholder="选择模型"
            size="small"
            style="width: 220px"
            :disabled="loading"
            @change="onModelChange"
          >
            <ElOption
              v-for="m in models"
              :key="m.value"
              :label="m.label"
              :value="m.value"
            >
              <ElTooltip :content="getModelDesc(m.value)" placement="right">
                <span>{{ m.label }}</span>
              </ElTooltip>
            </ElOption>
          </ElSelect>
          <ElButton
            size="small"
            :icon="Refresh"
            :loading="syncingModels"
            title="从官方接口同步可用模型"
            @click="syncModels"
          >
            模型同步
          </ElButton>
          <ElSelect
            v-model="selectedId"
            placeholder="选择角色模板"
            clearable
            class="template-select"
            @change="syncContentFromSelected"
          >
            <ElOption
              v-for="t in templates"
              :key="t.id"
              :label="t.name + (t.is_selected ? ' ✓' : '')"
              :value="t.id"
            />
          </ElSelect>
          <ElButton type="primary" size="small" :loading="saving" @click="saveCurrent">保存</ElButton>
          <ElButton
            v-if="selectedId"
            type="danger"
            size="small"
            link
            :icon="Delete"
            @click="doDelete(selectedId)"
          >
            删除
          </ElButton>
        </div>
      </template>

      <p class="tip">
        选择 Grok 或 Qwen 后管理对应角色模板；Token 配置中选择的 Agent 将启用其选中的模板
      </p>

      <div v-if="templates.length === 0 && !loading" class="empty-state">
        <ElEmpty description="暂无角色模板，请新建" :image-size="60" />
        <ElInput v-model="templateName" placeholder="模板名称（如：量化经理）" class="name-input" />
        <ElInput
          v-model="promptContent"
          type="textarea"
          :rows="12"
          placeholder="在此编辑角色设定内容，支持 Markdown..."
        />
        <ElButton type="primary" :loading="saving" @click="addNew">新建并保存</ElButton>
      </div>

      <template v-else>
        <div class="name-row">
          <span class="label">模板名称：</span>
          <ElInput v-model="templateName" placeholder="模板名称" class="name-input" />
        </div>
        <ElInput
          v-model="promptContent"
          type="textarea"
          :rows="16"
          placeholder="在此编辑角色设定内容，支持 Markdown..."
        />
        <div class="preview-section">
          <div class="preview-label">预览</div>
          <div v-if="previewHtml" class="preview-area markdown-body" v-html="previewHtml"></div>
          <ElEmpty v-else description="暂无内容" :image-size="60" />
        </div>
        <div class="actions">
          <ElButton type="primary" :loading="saving" @click="saveCurrent">保存</ElButton>
          <ElButton v-if="!selectedId" type="success" :loading="saving" @click="addNew">新建并保存</ElButton>
          <ElButton
            v-else-if="!currentTemplate?.is_selected"
            @click="doSelect(selectedId)"
          >
            设为当前选中
          </ElButton>
        </div>
      </template>
    </ElCard>
  </div>
</template>

<style scoped>
.agent-role-setting { max-width: 900px; }
.main-card { margin-bottom: 20px; }
.header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.template-select { width: 200px; }
.tip { font-size: 0.85rem; color: var(--el-text-color-secondary); margin: 0 0 16px; }
.empty-state { display: flex; flex-direction: column; gap: 12px; }
.name-input { max-width: 280px; }
.name-row { margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.name-row .label { font-size: 0.95rem; }

.preview-section {
  margin-top: 16px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  min-height: 80px;
}

.dark .preview-section {
  background: var(--el-fill-color);
}

.preview-label {
  font-size: 0.9rem;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.preview-area {
  margin: 0;
  padding: 8px 0;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  word-break: break-word;
}

.preview-area.markdown-body :deep(h1),
.preview-area.markdown-body :deep(h2),
.preview-area.markdown-body :deep(h3) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 600;
}

.preview-area.markdown-body :deep(h1) { font-size: 1.4em; }
.preview-area.markdown-body :deep(h2) { font-size: 1.2em; }
.preview-area.markdown-body :deep(h3) { font-size: 1.05em; }

.preview-area.markdown-body :deep(p) {
  margin: 0.5em 0;
}

.preview-area.markdown-body :deep(ul),
.preview-area.markdown-body :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.preview-area.markdown-body :deep(code) {
  padding: 0.15em 0.4em;
  background: var(--el-fill-color);
  border-radius: 4px;
  font-size: 0.9em;
}

.preview-area.markdown-body :deep(pre) {
  margin: 0.5em 0;
  padding: 12px;
  background: var(--el-fill-color);
  border-radius: 6px;
  overflow-x: auto;
}

.preview-area.markdown-body :deep(pre code) {
  padding: 0;
  background: transparent;
}

.preview-area.markdown-body :deep(blockquote) {
  margin: 0.5em 0;
  padding-left: 1em;
  border-left: 4px solid var(--el-border-color);
  color: var(--el-text-color-secondary);
}

.preview-area.markdown-body :deep(table) {
  margin: 0.5em 0;
  border-collapse: collapse;
  width: 100%;
}

.preview-area.markdown-body :deep(th),
.preview-area.markdown-body :deep(td) {
  padding: 6px 10px;
  border: 1px solid var(--el-border-color);
}

.preview-area.markdown-body :deep(th) {
  background: var(--el-fill-color);
  font-weight: 600;
}

.actions { margin-top: 16px; display: flex; gap: 12px; }

@media (max-width: 768px) {
  .actions { flex-wrap: wrap; }
}
</style>
