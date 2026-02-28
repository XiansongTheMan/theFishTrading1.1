<!--
  Token 配置 - Tushare 支持多条目、拖拽排序；其他 API Token
-->
<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import {
  ElCard,
  ElInput,
  ElButton,
  ElMessage,
  ElTag,
  ElSelect,
  ElOption,
} from "element-plus";
import { Plus, Delete } from "@element-plus/icons-vue";
import draggable from "vuedraggable";
import { getTokens, updateTokens, testToken, type TushareItem, type AiTokenItem } from "../api/config";

const loading = ref(false);
const saving = ref(false);
const backendOk = ref<boolean | null>(null);
const primaryDataSource = ref<"akshare" | "tushare">("tushare");
const loadedPrimarySource = ref<"akshare" | "tushare">("tushare");
const primaryAiAgent = ref<"grok" | "qwen">("grok");
const loadedPrimaryAiAgent = ref<"grok" | "qwen">("grok");
const grokList = ref<AiTokenItem[]>([]);
const qwenList = ref<AiTokenItem[]>([]);
const grokForm = ref<{ id: string; token: string; remark: string }[]>([]);
const qwenForm = ref<{ id: string; token: string; remark: string }[]>([]);
const tushareList = ref<TushareItem[]>([]);
const tushareForm = ref<{ id: string; token: string; remark: string }[]>([]);
const testStatus = ref<Record<string, "idle" | "testing" | "success" | "failed">>({});
const AKSHARE_TEST_KEY = "akshare";
const akshareErrorMsg = ref("");

async function load() {
  loading.value = true;
  try {
    const res = (await getTokens()) as {
      data?: { grok_list?: AiTokenItem[]; qwen_list?: AiTokenItem[]; primary_ai_agent?: string; tushare_list?: TushareItem[]; primary_data_source?: string };
    };
    grokList.value = res?.data?.grok_list ?? [];
    qwenList.value = res?.data?.qwen_list ?? [];
    tushareList.value = res?.data?.tushare_list ?? [];
    const agent = (res?.data?.primary_ai_agent || "grok").toLowerCase();
    primaryAiAgent.value = agent === "qwen" ? "qwen" : "grok";
    loadedPrimaryAiAgent.value = primaryAiAgent.value;
    const src = (res?.data?.primary_data_source || "tushare").toLowerCase();
    primaryDataSource.value = src === "akshare" ? "akshare" : "tushare";
    loadedPrimarySource.value = primaryDataSource.value;

    function toForm(list: AiTokenItem[]) {
      if (list.length > 0) {
        return list.map((it, i) => ({
          id: it.id || `ai_${i}_${Date.now()}`,
          token: it.has_value ? it.value_masked : "",
          remark: it.remark || (it.is_primary ? "主" : ""),
        }));
      }
      return [{ id: `ai_0_${Date.now()}`, token: "", remark: "主" }];
    }
    grokForm.value = toForm(grokList.value);
    qwenForm.value = toForm(qwenList.value);

    if (tushareList.value.length > 0) {
      tushareForm.value = tushareList.value.map((it, i) => ({
        id: it.id || `ts_${i}_${Date.now()}`,
        token: it.has_value ? it.value_masked : "",
        remark: it.remark || (it.is_primary ? "主" : ""),
      }));
    } else {
      tushareForm.value = [{ id: `ts_0_${Date.now()}`, token: "", remark: "主" }];
    }
  } catch {
    backendOk.value = false;
    grokList.value = [];
    qwenList.value = [];
    grokForm.value = [{ id: `ai_0_${Date.now()}`, token: "", remark: "主" }];
    qwenForm.value = [{ id: `ai_0_${Date.now()}`, token: "", remark: "主" }];
    tushareList.value = [];
    tushareForm.value = [{ id: `ts_0_${Date.now()}`, token: "", remark: "主" }];
  } finally {
    loading.value = false;
    if (backendOk.value === null) backendOk.value = true;
  }
}

function addTushare() {
  tushareForm.value.push({
    id: `ts_${Date.now()}`,
    token: "",
    remark: `备用${tushareForm.value.length}`,
  });
}

function removeTushare(idx: number) {
  if (tushareForm.value.length <= 1) return;
  tushareForm.value.splice(idx, 1);
}

function getTushareTestKey(idx: number) {
  return `tushare_${idx}`;
}

function getAiTestKey(agent: "grok" | "qwen", idx: number) {
  return `${agent}_${idx}`;
}

function addAiToken(agent: "grok" | "qwen") {
  const form = agent === "grok" ? grokForm : qwenForm;
  form.value.push({
    id: `ai_${Date.now()}`,
    token: "",
    remark: `备用${form.value.length}`,
  });
}

function removeAiToken(agent: "grok" | "qwen", idx: number) {
  const form = agent === "grok" ? grokForm : qwenForm;
  if (form.value.length <= 1) return;
  form.value.splice(idx, 1);
}

const currentAiPlaceholder = computed(() =>
  primaryAiAgent.value === "grok" ? "在 console.x.ai 获取 API Key" : "在 dashscope.console.aliyun.com 获取 API Key"
);

function buildAiPayload(form: { id: string; token: string; remark: string }[], list: AiTokenItem[]) {
  return form.map((f, i) => {
    const tokenRaw = (f.token || "").trim();
    const remark = (f.remark || "").trim() || "主";
    const existing = list[i];
    const isUnchanged = existing?.has_value && tokenRaw === existing.value_masked;
    if (isUnchanged) return { remark, keep_existing: true };
    if (!tokenRaw) return { remark, token: null };
    return { token: tokenRaw, remark };
  });
}

async function apply() {
  saving.value = true;
  try {
    const tsPayload = tushareForm.value.map((f, i) => {
      const tokenRaw = (f.token || "").trim();
      const remark = (f.remark || "").trim() || "主";
      const existing = tushareList.value[i];
      const isUnchanged = existing?.has_value && tokenRaw === existing.value_masked;
      if (isUnchanged) return { remark, keep_existing: true };
      if (!tokenRaw) return { remark, token: null };
      return { token: tokenRaw, remark };
    });

    const grokPayload = buildAiPayload(grokForm.value, grokList.value);
    const qwenPayload = buildAiPayload(qwenForm.value, qwenList.value);

    const effectiveGrok = grokPayload.filter((p) => ("token" in p && p.token) || ("keep_existing" in p && p.keep_existing)).length;
    const effectiveQwen = qwenPayload.filter((p) => ("token" in p && p.token) || ("keep_existing" in p && p.keep_existing)).length;
    const grokChanged =
      grokForm.value.length !== grokList.value.length ||
      grokForm.value.some((f, i) => {
        const ex = grokList.value[i];
        if (!ex) return f.token.trim() !== "";
        return f.token !== ex.value_masked || (!f.token.trim() && ex.has_value) || f.remark !== ex.remark;
      });
    const qwenChanged =
      qwenForm.value.length !== qwenList.value.length ||
      qwenForm.value.some((f, i) => {
        const ex = qwenList.value[i];
        if (!ex) return f.token.trim() !== "";
        return f.token !== ex.value_masked || (!f.token.trim() && ex.has_value) || f.remark !== ex.remark;
      });
    const effectiveTushareCount = tsPayload.filter(
      (p) => ("token" in p && p.token) || ("keep_existing" in p && p.keep_existing)
    ).length;
    const hasChanges =
      primaryAiAgent.value !== loadedPrimaryAiAgent.value ||
      primaryDataSource.value !== loadedPrimarySource.value ||
      effectiveTushareCount !== tushareList.value.filter((t) => t.has_value).length ||
      tushareForm.value.some((f, i) => {
        const existing = tushareList.value[i];
        if (!existing) return f.token.trim() !== "";
        const sameVal = f.token === existing.value_masked || (!f.token.trim() && !existing.has_value);
        return !sameVal;
      }) ||
      grokChanged ||
      qwenChanged;

    if (!hasChanges) {
      ElMessage.info("请输入要设置的 Token 后点击应用");
      saving.value = false;
      return;
    }

    const payload = {
      tushare_list: tsPayload,
      grok_list: grokPayload,
      qwen_list: qwenPayload,
      primary_ai_agent: primaryAiAgent.value,
      primary_data_source: primaryDataSource.value,
    };
    await updateTokens(payload);
    tushareForm.value.forEach((_, i) => (testStatus.value[getTushareTestKey(i)] = "idle"));
    grokForm.value.forEach((_, i) => (testStatus.value[getAiTestKey("grok", i)] = "idle"));
    qwenForm.value.forEach((_, i) => (testStatus.value[getAiTestKey("qwen", i)] = "idle"));
    ElMessage.success("Token 已保存并应用");
    await load();
    window.dispatchEvent(new CustomEvent("data-source-updated"));
  } catch (e: unknown) {
    const err = e as Error & { _toastShown?: boolean };
    if (!err?._toastShown) ElMessage.error(err?.message || "保存失败");
    console.error("Token 应用失败:", e);
  } finally {
    saving.value = false;
  }
}

async function testAiToken(agent: "grok" | "qwen", idx: number) {
  const key = getAiTestKey(agent, idx);
  testStatus.value[key] = "testing";
  try {
    const form = agent === "grok" ? grokForm : qwenForm;
    const list = agent === "grok" ? grokList : qwenList;
    const row = form.value[idx];
    const val = (row?.token || "").trim();
    const existing = list.value[idx];
    const useStored = existing?.has_value && val === existing.value_masked;
    const res = (await testToken(agent, useStored ? undefined : val || undefined, idx)) as {
      data?: { ok?: boolean; message?: string };
    };
    const ok = res?.data?.ok ?? false;
    testStatus.value[key] = ok ? "success" : "failed";
    if (ok) ElMessage.success("连接成功");
    else if (res?.data?.message) ElMessage.warning(res.data.message);
  } catch (e: unknown) {
    testStatus.value[key] = "failed";
    const err = e as Error & { _toastShown?: boolean };
    if (!err?._toastShown) ElMessage.error(err?.message || "连接测试失败");
  }
}

async function testAkshare() {
  testStatus.value[AKSHARE_TEST_KEY] = "testing";
  akshareErrorMsg.value = "";
  try {
    const res = (await testToken(AKSHARE_TEST_KEY)) as { data?: { ok?: boolean; message?: string } };
    const ok = res?.data?.ok ?? false;
    testStatus.value[AKSHARE_TEST_KEY] = ok ? "success" : "failed";
    if (ok) {
      ElMessage.success("连接成功");
      akshareErrorMsg.value = "";
    } else {
      akshareErrorMsg.value = res?.data?.message || "连接失败";
      ElMessage.warning(akshareErrorMsg.value);
    }
  } catch (e: unknown) {
    testStatus.value[AKSHARE_TEST_KEY] = "failed";
    const err = e as Error & { _toastShown?: boolean };
    akshareErrorMsg.value = err?.message || "连接测试失败";
    if (!err?._toastShown) ElMessage.error(akshareErrorMsg.value);
  }
}

async function testTushare(idx: number) {
  const key = getTushareTestKey(idx);
  testStatus.value[key] = "testing";
  try {
    const row = tushareForm.value[idx];
    const val = (row?.token || "").trim();
    const existing = tushareList.value[idx];
    const useStored = existing?.has_value && val === existing.value_masked;
    const res = (await testToken("tushare", useStored ? undefined : val || undefined, idx)) as {
      data?: { ok?: boolean; message?: string };
    };
    const ok = res?.data?.ok ?? false;
    testStatus.value[key] = ok ? "success" : "failed";
    if (ok) ElMessage.success("连接成功");
    else if (res?.data?.message) ElMessage.warning(res.data.message);
  } catch (e: unknown) {
    testStatus.value[key] = "failed";
    const err = e as Error & { _toastShown?: boolean };
    if (!err?._toastShown) ElMessage.error(err?.message || "连接测试失败");
  }
}

function onTushareDragEnd() {
  // 拖拽后 tushareForm 已由 vuedraggable 更新顺序
}

onMounted(load);
</script>

<template>
  <div class="token-view">
    <h2 class="page-title">Token 配置</h2>
    <div v-if="backendOk === false" class="backend-warn">
      无法连接后端，请确保 backend 在 <code>localhost:8000</code> 运行，且 MongoDB 已启动。
    </div>
    <ElCard shadow="never" class="card" v-loading="loading">
      <template #header>
        <span>API Token</span>
        <ElButton type="primary" size="small" :loading="saving" @click="apply">应用</ElButton>
      </template>

      <!-- 主要金融数据源 -->
      <div class="token-section data-source-section">
        <div class="section-header">
          <span class="section-label">主要金融数据源：</span>
          <ElSelect v-model="primaryDataSource" size="small" style="width: 140px">
            <ElOption label="tushare" value="tushare" />
            <ElOption label="akshare" value="akshare" />
          </ElSelect>
          <template v-if="primaryDataSource === 'akshare'">
            <ElTag
              v-if="testStatus[AKSHARE_TEST_KEY] === 'success'"
              type="success"
              size="small"
            >
              连接成功
            </ElTag>
            <ElTag v-else-if="testStatus[AKSHARE_TEST_KEY] === 'failed'" type="warning" size="small">
              连接失败
            </ElTag>
            <ElButton
              type="primary"
              size="small"
              :loading="testStatus[AKSHARE_TEST_KEY] === 'testing'"
              @click="testAkshare"
            >
              akshare 连接测试
            </ElButton>
          </template>
        </div>
        <p class="section-tip">基金/股票数据将优先使用所选数据源，失败时自动切换另一数据源</p>
        <div v-if="primaryDataSource === 'akshare' && testStatus[AKSHARE_TEST_KEY] === 'failed' && akshareErrorMsg" class="akshare-error">
          <span class="error-label">失败原因：</span>{{ akshareErrorMsg }}
          <br />
          <span class="error-hint">提示：akshare 数据来自东方财富等网站，若连接失败请尝试先登录东方财富 (eastmoney.com) 后再试。</span>
        </div>
      </div>

      <!-- Tushare 多条目 -->
      <div class="token-section">
        <div class="section-header">
          <span class="section-label">tushare：</span>
          <ElButton type="primary" link size="small" :icon="Plus" @click="addTushare">
            添加
          </ElButton>
        </div>
        <draggable
          v-model="tushareForm"
          item-key="id"
          handle=".drag-handle"
          @end="onTushareDragEnd"
          class="tushare-draggable"
        >
          <template #item="{ element, index }">
            <div class="token-row tushare-row">
              <span class="drag-handle" title="拖拽排序">⋮⋮</span>
              <div class="tushare-fields">
                <ElInput
                  v-model="element.remark"
                  placeholder="备注（主/备用1）"
                  class="remark-input"
                  autocomplete="off"
                />
                <ElInput
                  v-model="element.token"
                  type="text"
                  clearable
                  placeholder="在 tushare.pro 注册获取"
                  autocomplete="off"
                />
              </div>
              <div class="tushare-actions">
                <ElTag
                  v-if="!element.token?.trim() && !tushareList[index]?.has_value"
                  type="info"
                  size="small"
                >
                  待接入
                </ElTag>
                <ElTag
                  v-else-if="testStatus[getTushareTestKey(index)] === 'success'"
                  type="success"
                  size="small"
                >
                  连接成功
                </ElTag>
                <ElTag v-else type="warning" size="small">未连接成功</ElTag>
                <ElButton
                  type="primary"
                  size="small"
                  :loading="testStatus[getTushareTestKey(index)] === 'testing'"
                  @click="testTushare(index)"
                >
                  连接测试
                </ElButton>
                <ElButton
                  v-if="tushareForm.length > 1"
                  type="danger"
                  link
                  size="small"
                  :icon="Delete"
                  @click="removeTushare(index)"
                >
                  删除
                </ElButton>
              </div>
            </div>
          </template>
        </draggable>
      </div>

      <!-- AI Agent：grok / qwen 二选一，多 Token + 备注，第一个为选中 -->
      <div class="token-section ai-agent-section">
        <div class="section-header">
          <span class="section-label">AI 模型 / Agent：</span>
          <ElSelect v-model="primaryAiAgent" size="small" style="width: 160px">
            <ElOption label="Grok (x.ai)" value="grok" />
            <ElOption label="通义千问 (Qwen)" value="qwen" />
          </ElSelect>
          <ElButton type="primary" link size="small" :icon="Plus" @click="addAiToken(primaryAiAgent)">
            添加 Token
          </ElButton>
          <ElButton type="primary" size="small" :loading="saving" @click="apply">
            保存
          </ElButton>
        </div>
        <p class="section-tip">
          选择 Agent 后显示对应 Token 列表，可添加多个 Token 并写备注；拖拽排序，第一个为选中的 Token
        </p>
        <draggable
          v-if="primaryAiAgent === 'grok'"
          v-model="grokForm"
          item-key="id"
          handle=".drag-handle"
          class="tushare-draggable"
        >
          <template #item="{ element, index }">
            <div class="token-row tushare-row">
              <span class="drag-handle" title="拖拽排序，第一个为选中">⋮⋮</span>
              <div class="tushare-fields">
                <ElInput v-model="element.remark" placeholder="备注（主/备用1）" class="remark-input" autocomplete="off" />
                <ElInput v-model="element.token" type="text" clearable autocomplete="off" :placeholder="currentAiPlaceholder" />
              </div>
              <div class="tushare-actions">
                <ElTag v-if="index === 0" type="success" size="small">当前选中</ElTag>
                <ElTag v-else-if="!element.token?.trim() && !grokList[index]?.has_value" type="info" size="small">待接入</ElTag>
                <ElTag v-else-if="testStatus[getAiTestKey('grok', index)] === 'success'" type="success" size="small">连接成功</ElTag>
                <ElTag v-else type="warning" size="small">未连接成功</ElTag>
                <ElButton type="primary" size="small" :loading="testStatus[getAiTestKey('grok', index)] === 'testing'" @click="testAiToken('grok', index)">
                  Grok API 连接测试
                </ElButton>
                <ElButton v-if="grokForm.length > 1" type="danger" link size="small" :icon="Delete" @click="removeAiToken('grok', index)">删除</ElButton>
              </div>
            </div>
          </template>
        </draggable>
        <draggable
          v-else
          v-model="qwenForm"
          item-key="id"
          handle=".drag-handle"
          class="tushare-draggable"
        >
          <template #item="{ element, index }">
            <div class="token-row tushare-row">
              <span class="drag-handle" title="拖拽排序，第一个为选中">⋮⋮</span>
              <div class="tushare-fields">
                <ElInput v-model="element.remark" placeholder="备注（主/备用1）" class="remark-input" autocomplete="off" />
                <ElInput v-model="element.token" type="text" clearable autocomplete="off" :placeholder="currentAiPlaceholder" />
              </div>
              <div class="tushare-actions">
                <ElTag v-if="index === 0" type="success" size="small">当前选中</ElTag>
                <ElTag v-else-if="!element.token?.trim() && !qwenList[index]?.has_value" type="info" size="small">待接入</ElTag>
                <ElTag v-else-if="testStatus[getAiTestKey('qwen', index)] === 'success'" type="success" size="small">连接成功</ElTag>
                <ElTag v-else type="warning" size="small">未连接成功</ElTag>
                <ElButton type="primary" size="small" :loading="testStatus[getAiTestKey('qwen', index)] === 'testing'" @click="testAiToken('qwen', index)">
                  通义千问 API 连接测试
                </ElButton>
                <ElButton v-if="qwenForm.length > 1" type="danger" link size="small" :icon="Delete" @click="removeAiToken('qwen', index)">删除</ElButton>
              </div>
            </div>
          </template>
        </draggable>
      </div>

      <div v-if="grokList.length === 0 && qwenList.length === 0 && tushareForm.length === 0 && !loading" class="empty-tip">
        暂无可配置的 Token
      </div>
    </ElCard>
  </div>
</template>

<style scoped>
.token-view {
  max-width: 720px;
}

.page-title {
  margin: 0 0 20px;
  color: var(--el-text-color-primary);
}

.backend-warn {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning-dark-2);
  border-radius: 8px;
  font-size: 0.9rem;
}

.backend-warn code {
  background: rgba(0, 0, 0, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
}

.card {
  margin-bottom: 20px;
}

.token-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.section-label {
  font-size: 0.95rem;
  color: var(--el-text-color-primary);
}

.section-tip {
  margin: 0 0 12px;
  font-size: 0.85rem;
  color: var(--el-text-color-secondary);
}

.akshare-error {
  margin-top: 8px;
  padding: 12px;
  background: var(--el-color-warning-light-9);
  border-radius: 8px;
  font-size: 0.9rem;
  color: var(--el-color-warning-dark-2);
}

.akshare-error .error-label {
  font-weight: 600;
}

.akshare-error .error-hint {
  font-size: 0.85rem;
  color: var(--el-text-color-secondary);
  margin-top: 6px;
  display: inline-block;
}

.tushare-draggable {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.token-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tushare-row {
  flex-direction: row;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.drag-handle {
  cursor: grab;
  color: var(--el-text-color-placeholder);
  font-size: 14px;
  user-select: none;
}

.drag-handle:active {
  cursor: grabbing;
}

.tushare-fields {
  flex: 1;
  display: flex;
  gap: 8px;
  align-items: center;
}

.remark-input {
  width: 100px;
  flex-shrink: 0;
}

.tushare-fields .el-input {
  flex: 1;
}

.tushare-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
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
