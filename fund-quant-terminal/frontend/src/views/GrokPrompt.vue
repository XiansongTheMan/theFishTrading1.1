<!-- Grok AI 角色设定（实时可编辑） -->
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

const promptContent = ref("");
const loading = ref(false);
const saving = ref(false);
const historyVisible = ref(false);
const historyList = ref<{ id: string; version: number; updated_at: string }[]>([]);
const selectedVersion = ref<number | null>(null);
const versionInfo = ref<{ version?: number; updated_at?: string } | null>(null);

async function loadLatest() {
  loading.value = true;
  try {
    const res = (await getGrokPrompt()) as {
      data?: { content: string; version?: number; updated_at?: string } | null;
    };
    const d = res?.data;
    if (d?.content != null) {
      promptContent.value = d.content;
      versionInfo.value = d.version != null ? { version: d.version, updated_at: d.updated_at } : null;
    } else {
      promptContent.value = "";
      versionInfo.value = null;
    }
    selectedVersion.value = null;
    ElMessage.success("已加载最新版本");
  } catch {
    promptContent.value = "";
    versionInfo.value = null;
    ElMessage.error("加载失败");
  } finally {
    loading.value = false;
  }
}

async function saveNew() {
  if (!promptContent.value.trim()) {
    ElMessage.warning("请输入提示词内容");
    return;
  }
  saving.value = true;
  try {
    const res = (await saveGrokPrompt(promptContent.value)) as {
      data?: { version: number; updated_at: string };
    };
    if (res?.data) {
      versionInfo.value = { version: res.data.version, updated_at: res.data.updated_at };
      ElMessage.success(`已保存为新版本 v${res.data.version}`);
      await loadHistory();
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
    historyVisible.value = true;
  } catch {
    historyList.value = [];
    ElMessage.error("加载历史失败");
  }
}

async function loadVersion(v: number) {
  loading.value = true;
  try {
    const res = (await getGrokPrompt(v)) as {
      data?: { content: string; version?: number; updated_at?: string } | null;
    };
    const d = res?.data;
    if (d?.content != null) {
      promptContent.value = d.content;
      versionInfo.value = d.version != null ? { version: d.version, updated_at: d.updated_at } : null;
    }
  } catch {
    ElMessage.error("加载该版本失败");
  } finally {
    loading.value = false;
  }
}

watch(selectedVersion, (v) => {
  if (v != null) loadVersion(v);
});

// Markdown 简易预览：保留换行与格式
const previewText = computed(() => promptContent.value || "");

onMounted(loadLatest);
</script>

<template>
  <div class="grok-prompt">
    <ElCard shadow="never" class="grok-card">
      <template #header>
        <span>Grok AI 角色设定（实时可编辑）</span>
        <span v-if="versionInfo?.version" class="version-badge">
          v{{ versionInfo.version }}
          <span v-if="versionInfo.updated_at" class="updated">{{
            versionInfo.updated_at.slice(0, 19)
          }}</span>
        </span>
      </template>

      <ElInput
        v-model="promptContent"
        type="textarea"
        :rows="20"
        placeholder="在此编辑 Grok 4.2 系统角色提示词，支持 Markdown 格式..."
      />

      <div class="preview-section">
        <div class="preview-label">预览</div>
        <pre v-if="previewText" class="preview-area">{{ previewText }}</pre>
        <ElEmpty v-else description="暂无内容" :image-size="60" />
      </div>

      <div class="actions">
        <ElButton type="primary" :loading="loading" @click="loadLatest">
          加载最新版本
        </ElButton>
        <ElButton type="success" :loading="saving" @click="saveNew">
          保存新版本
        </ElButton>
        <ElButton @click="loadHistory">查看历史</ElButton>
      </div>
    </ElCard>

    <ElCard v-if="historyVisible" shadow="never" class="history-card">
      <template #header>历史版本</template>
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
        v-if="historyList.length === 0"
        description="暂无历史版本"
        :image-size="50"
      />
    </ElCard>
  </div>
</template>

<style scoped>
.grok-prompt {
  max-width: 900px;
}

.grok-card {
  margin-bottom: 20px;
}

.version-badge {
  margin-left: 12px;
  font-size: 0.85rem;
  color: var(--el-text-color-secondary);
}

.updated {
  margin-left: 8px;
}

.preview-section {
  margin-top: 16px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  min-height: 80px;
}

/* 深色模式：Element Plus 变量自动切换，或父级 .dark */
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

.history-card {
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
