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
} from "element-plus";
import { Plus, Delete } from "@element-plus/icons-vue";
import {
  listAgentTemplates,
  createAgentTemplate,
  updateAgentTemplate,
  deleteAgentTemplate,
  selectAgentTemplate,
  type AgentTemplateItem,
} from "../api/grok";

const agent = ref<"grok" | "qwen">("grok");
const loading = ref(false);
const saving = ref(false);
const templates = ref<AgentTemplateItem[]>([]);
const selectedId = ref("");
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
      data?: { items?: AgentTemplateItem[]; selected_id?: string; primary_ai_agent?: string };
    };
    templates.value = res?.data?.items ?? [];
    selectedId.value = res?.data?.selected_id ?? "";
    primaryAiAgent.value = (res?.data?.primary_ai_agent || "grok") === "qwen" ? "qwen" : "grok";
    if (!ag && templates.value.length > 0 && !selectedId.value) {
      selectedId.value = templates.value[0].id;
    }
    syncContentFromSelected();
  } catch {
    templates.value = [];
    selectedId.value = "";
    ElMessage.error("加载失败");
  } finally {
    loading.value = false;
  }
}

function syncContentFromSelected() {
  const t = currentTemplate.value;
  if (t) {
    templateName.value = t.name;
    promptContent.value = t.content;
  } else {
    templateName.value = "";
    promptContent.value = "";
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
    await updateAgentTemplate(selectedId.value, {
      name,
      content: promptContent.value,
    });
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

onMounted(() => {
  load();
});
</script>

<template>
  <div class="agent-prompt">
    <ElCard shadow="never" class="main-card">
      <template #header>
        <span>Agent 角色设定</span>
        <div class="header-actions">
          <ElSelect v-model="agent" size="small" style="width: 140px" @change="load">
            <ElOption label="Grok (x.ai)" value="grok" />
            <ElOption label="通义千问 (Qwen)" value="qwen" />
          </ElSelect>
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
          <ElButton type="primary" size="small" :loading="saving" @click="saveCurrent">
            保存
          </ElButton>
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
.agent-prompt { max-width: 900px; }
.main-card { margin-bottom: 20px; }
.header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.template-select { width: 200px; }
.tip { font-size: 0.85rem; color: var(--el-text-color-secondary); margin: 0 0 16px; }
.empty-state { display: flex; flex-direction: column; gap: 12px; }
.name-input { max-width: 280px; }
.name-row { margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.name-row .label { font-size: 0.95rem; }
.preview-section { margin-top: 16px; padding: 12px; background: var(--el-fill-color-light); border-radius: 6px; min-height: 80px; }
.preview-label { font-size: 0.9rem; color: var(--el-text-color-secondary); margin-bottom: 8px; }
.preview-area { margin: 0; padding: 8px 0; font-size: 0.9rem; line-height: 1.6; word-break: break-word; }
.preview-area.markdown-body :deep(h1), .preview-area.markdown-body :deep(h2), .preview-area.markdown-body :deep(h3) {
  margin-top: 1em; margin-bottom: 0.5em; font-weight: 600;
}
.preview-area.markdown-body :deep(p) { margin: 0.5em 0; }
.preview-area.markdown-body :deep(ul), .preview-area.markdown-body :deep(ol) {
  margin: 0.5em 0; padding-left: 1.5em;
}
.preview-area.markdown-body :deep(code) {
  padding: 0.15em 0.4em; background: var(--el-fill-color); border-radius: 4px; font-size: 0.9em;
}
.preview-area.markdown-body :deep(pre) {
  margin: 0.5em 0; padding: 12px; background: var(--el-fill-color); border-radius: 6px; overflow-x: auto;
}
.actions { margin-top: 16px; display: flex; gap: 12px; }
</style>
