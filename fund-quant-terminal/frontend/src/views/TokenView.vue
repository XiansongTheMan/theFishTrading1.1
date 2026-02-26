<!--
  =====================================================
  Token 配置 - 展示当前使用与未来将使用的 API Token
  格式：api 名称：（token 输入框）
  =====================================================
-->
<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  ElCard,
  ElInput,
  ElButton,
  ElMessage,
  ElTag,
} from "element-plus";
import { getTokens, updateTokens, testToken, type TokenItem } from "../api/config";

const loading = ref(false);
const saving = ref(false);
const items = ref<TokenItem[]>([]);
const formValues = ref<Record<string, string>>({});
const testStatus = ref<Record<string, "idle" | "testing" | "success" | "failed">>({});

async function load() {
  loading.value = true;
  try {
    const res = (await getTokens()) as { data?: { items?: TokenItem[] } };
    items.value = res?.data?.items ?? [];
    formValues.value = {};
    items.value.forEach((it) => {
      formValues.value[it.key] = "";
    });
  } catch {
    items.value = [];
  } finally {
    loading.value = false;
  }
}

async function apply() {
  saving.value = true;
  try {
    const toUpdate: Record<string, string> = {};
    for (const [k, v] of Object.entries(formValues.value)) {
      const val = v != null ? String(v).trim() : "";
      if (val) toUpdate[k] = val;
    }
    if (Object.keys(toUpdate).length === 0) {
      ElMessage.info("请输入要设置的 Token 后点击应用");
      saving.value = false;
      return;
    }
    await updateTokens(toUpdate);
    Object.keys(toUpdate).forEach((k) => { testStatus.value[k] = "idle"; });
    ElMessage.success("Token 已保存并应用");
    await load();
  } catch {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
}

async function clearOne(key: string) {
  try {
    await updateTokens({ [key]: "" });
    testStatus.value[key] = "idle";
    ElMessage.success("已清除");
    await load();
  } catch {
    ElMessage.error("清除失败");
  }
}

async function testConnection(item: TokenItem) {
  const key = item.key;
  testStatus.value[key] = "testing";
  try {
    const res = (await testToken(key, formValues.value[key] || undefined)) as {
      data?: { ok?: boolean; message?: string };
    };
    const ok = res?.data?.ok ?? false;
    testStatus.value[key] = ok ? "success" : "failed";
    if (ok) {
      ElMessage.success("连接成功");
    }
  } catch {
    testStatus.value[key] = "failed";
  }
}

onMounted(load);
</script>

<template>
  <div class="token-view">
    <h2 class="page-title">Token 配置</h2>

    <ElCard shadow="never" class="card" v-loading="loading">
      <template #header>
        <span>API Token</span>
        <ElButton type="primary" size="small" :loading="saving" @click="apply">
          应用
        </ElButton>
      </template>

      <div class="token-list">
        <div
          v-for="item in items"
          :key="item.key"
          class="token-row"
        >
          <label class="token-label">
            {{ item.label }}：
            <ElTag v-if="item.status === 'using'" type="success" size="small">
              使用中
            </ElTag>
            <ElTag v-else-if="item.status === 'future'" type="info" size="small">
              待接入
            </ElTag>
            <ElTag v-if="testStatus[item.key] === 'failed'" type="danger" size="small">
              连接失败
            </ElTag>
          </label>
          <div class="token-input-row">
            <ElInput
              v-model="formValues[item.key]"
              type="password"
              show-password
              :placeholder="item.has_value ? `已配置（${item.value_masked}）` : item.placeholder"
            />
            <ElButton
              type="primary"
              size="small"
              :loading="testStatus[item.key] === 'testing'"
              @click="testConnection(item)"
            >
              连接测试
            </ElButton>
            <ElButton
              v-if="item.has_value"
              type="info"
              link
              size="small"
              @click="clearOne(item.key)"
            >
              清除并应用
            </ElButton>
          </div>
        </div>
      </div>

      <div v-if="items.length === 0 && !loading" class="empty-tip">
        暂无可配置的 Token
      </div>
    </ElCard>
  </div>
</template>

<style scoped>
.token-view {
  max-width: 640px;
}

.page-title {
  margin: 0 0 20px;
  color: var(--el-text-color-primary);
}

.card {
  margin-bottom: 20px;
}

.token-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.token-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.token-label {
  font-size: 0.95rem;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.token-input-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.token-input-row .el-input {
  flex: 1;
}

.empty-tip {
  padding: 24px;
  text-align: center;
  color: var(--el-text-color-secondary);
}
</style>
