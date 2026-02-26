<!--
  =====================================================
  Grok AI 角色设定 - 提示词编辑与历史版本
  =====================================================
-->
<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import {
  ElCard,
  ElInput,
  ElButton,
  ElMessage,
  ElSelect,
  ElOption,
  ElEmpty,
} from "element-plus";
import { getGrokPrompt, saveGrokPrompt, getGrokPromptHistory } from "../api/grok";

const content = ref("");
const loading = ref(false);
const saving = ref(false);
const versionInfo = ref<{ version?: number; updated_at?: string } | null>(null);
const historyList = ref<{ id: string; version: number; updated_at: string }[]>([]);
const selectedVersion = ref<number | null>(null);

watch(selectedVersion, (v) => {
  if (v != null) loadVersion(v);
});

async function loadLatest() {
  loading.value = true;
  try {
    const res = (await getGrokPrompt()) as { data?: { content: string; version: number; updated_at?: string } | null };
    const d = res?.data;
    if (d?.content != null) {
      content.value = d.content;
      versionInfo.value = { version: d.version, updated_at: d.updated_at };
    } else {
      content.value = "";
      versionInfo.value = null;
    }
    selectedVersion.value = null;
    ElMessage.success("已加载最新版本");
  } catch (e) {
    ElMessage.error("加载失败");
    content.value = "";
    versionInfo.value = null;
  } finally {
    loading.value = false;
  }
}

async function loadVersion(v: number) {
  loading.value = true;
  try {
    const res = (await getGrokPrompt(v)) as { data?: { content: string; version: number; updated_at?: string } | null };
    const d = res?.data;
    if (d?.content != null) {
      content.value = d.content;
      versionInfo.value = { version: d.version, updated_at: d.updated_at };
    }
  } catch {
    ElMessage.error("加载该版本失败");
  } finally {
    loading.value = false;
  }
}

async function saveNew() {
  if (!content.value.trim()) {
    ElMessage.warning("请输入提示词内容");
    return;
  }
  saving.value = true;
  try {
    const res = (await saveGrokPrompt(content.value)) as {
      data?: { version: number; updated_at: string };
    };
    const d = res?.data;
    if (d) {
      versionInfo.value = { version: d.version, updated_at: d.updated_at };
      await loadHistory();
      ElMessage.success(`已保存为新版本 v${d.version}`);
    }
  } catch {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
}

async function loadHistory() {
  try {
    const res = (await getGrokPromptHistory()) as {
      data?: { id: string; version: number; updated_at: string }[];
    };
    historyList.value = res?.data ?? [];
  } catch {
    historyList.value = [];
  }
}

// Markdown 简易预览：换行保留，代码块等用 pre 展示
const previewHtml = computed(() => {
  const t = content.value || "";
  return t
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br>");
});

onMounted(() => {
  loadLatest();
  loadHistory();
});
</script>

<template>
  <div class="grok-prompt-view">
    <h2 class="page-title">Grok AI 角色设定</h2>

    <ElCard shadow="never" class="card-main">
      <template #header>
        <span>提示词内容</span>
        <span v-if="versionInfo?.version" class="version-tag">
          当前版本 v{{ versionInfo.version }}
          <span v-if="versionInfo.updated_at" class="updated-at">
            {{ versionInfo.updated_at.slice(0, 19) }}
          </span>
        </span>
      </template>

      <ElInput
        v-model="content"
        type="textarea"
        :rows="12"
        placeholder="在此编辑 Grok 4.2 系统角色提示词..."
        class="textarea-input"
        resize="vertical"
      />
      <div class="preview-section">
        <div class="preview-label">预览</div>
        <div
          v-if="content"
          class="preview-content"
          v-html="previewHtml"
        />
        <ElEmpty v-else description="暂无内容" :image-size="60" />
      </div>
      <div class="actions">
        <ElButton type="primary" :loading="loading" @click="loadLatest">
          加载最新
        </ElButton>
        <ElButton type="success" :loading="saving" @click="saveNew">
          保存新版本
        </ElButton>
        <ElButton @click="loadHistory">刷新历史</ElButton>
      </div>
    </ElCard>

    <ElCard shadow="never" class="card-history">
      <template #header>历史版本</template>
      <div class="history-list">
        <ElSelect
          v-model="selectedVersion"
          placeholder="选择版本查看"
          clearable
          class="history-select"
        >
          <ElOption
            v-for="h in historyList"
            :key="h.id"
            :label="`v${h.version} - ${h.updated_at?.slice(0, 19) ?? ''}`"
            :value="h.version"
          />
        </ElSelect>
        <ElEmpty
          v-if="historyList.length === 0 && !loading"
          description="暂无历史版本"
          :image-size="50"
        />
      </div>
    </ElCard>
  </div>
</template>

<style scoped>
.grok-prompt-view {
  max-width: 900px;
}

.page-title {
  margin: 0 0 20px;
  color: var(--el-text-color-primary);
}

.card-main {
  margin-bottom: 20px;
}

.version-tag {
  margin-left: 12px;
  font-size: 0.85rem;
  color: var(--el-text-color-secondary);
}

.updated-at {
  margin-left: 8px;
}

.textarea-input {
  margin-bottom: 16px;
}

.preview-section {
  margin-top: 16px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  min-height: 80px;
}

.layout-container.dark .preview-section,
.dark .preview-section {
  background: var(--el-fill-color);
}

.preview-label {
  font-size: 0.9rem;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.preview-content {
  font-family: inherit;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}

.card-history {
  margin-bottom: 20px;
}

.history-select {
  width: 100%;
  max-width: 320px;
}

@media (max-width: 768px) {
  .actions {
    flex-wrap: wrap;
  }
}
</style>
