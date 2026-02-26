<!-- Grok AI 角色设定 - textarea + 保存 -->
<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElCard, ElInput, ElButton, ElMessage } from "element-plus";
import { getGrokPrompt, saveGrokPrompt } from "../api/grok";

const content = ref("");
const loading = ref(false);
const saving = ref(false);

async function loadLatest() {
  loading.value = true;
  try {
    const res = (await getGrokPrompt()) as { data?: { content: string } | null };
    content.value = res?.data?.content ?? "";
  } catch {
    content.value = "";
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  try {
    await saveGrokPrompt(content.value);
    ElMessage.success("保存成功");
  } catch {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
}

onMounted(loadLatest);
</script>

<template>
  <div class="grok-prompt">
    <h2 class="page-title">Grok AI 角色设定</h2>
    <ElCard shadow="never">
      <ElInput
        v-model="content"
        type="textarea"
        :rows="14"
        placeholder="在此编辑 Grok 4.2 系统角色提示词..."
      />
      <div class="actions">
        <ElButton type="primary" :loading="loading" @click="loadLatest">加载最新</ElButton>
        <ElButton type="success" :loading="saving" @click="save">保存</ElButton>
      </div>
    </ElCard>
  </div>
</template>

<style scoped>
.grok-prompt {
  max-width: 800px;
}
.page-title {
  margin: 0 0 20px;
}
.actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}
</style>
