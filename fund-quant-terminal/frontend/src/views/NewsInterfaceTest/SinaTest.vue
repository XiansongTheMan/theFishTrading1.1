<!--
  新浪财经 - 新闻接口测试
  二级 Tab：国际、市场、其他、焦点、公司、宏观、两会、观点
  category 对应 international, market, other, focus, company, macro, lianghui, opinion
-->
<script setup lang="ts">
import { ref, computed, watch } from "vue";
import {
  ElCard,
  ElDivider,
  ElEmpty,
  ElTabs,
  ElTabPane,
  ElInputNumber,
  ElButton,
  ElCollapse,
  ElCollapseItem,
  ElForm,
  ElFormItem,
  ElSwitch,
  ElMessage,
  ElLoading,
  ElTimeline,
  ElTimelineItem,
  ElTag,
  ElLink,
  ElTooltip,
  type LoadingInstance,
} from "element-plus";
import { sinaTest } from "@/news/api/sina";
import { typeOptions, defaultTypeVal } from "@/news/config/sina";

interface ParsedItem {
  title: string;
  published_time: string | null;
  summary: string;
  url: string | null;
  sentiment?: number;
}

const typeVal = ref(defaultTypeVal);
const limitVal = ref(10);
const saveToDb = ref(false);
const loading = ref(false);
const result = ref<Record<string, unknown> | null>(null);
let loadingInstance: LoadingInstance | null = null;

const parsedList = computed<ParsedItem[]>(() => {
  const r = result.value as { parsed?: ParsedItem[] } | null;
  return r?.parsed ?? [];
});

const showTimeline = computed(() => parsedList.value.length > 0);

const rawJson = computed(() => {
  if (!result.value) return "";
  try {
    return JSON.stringify(result.value, null, 2);
  } catch {
    return String(result.value);
  }
});

function formatBeijingTime(isoStr: string | number | null | undefined): string {
  if (isoStr == null) return "—";
  let s: string;
  if (typeof isoStr === "number") {
    const d = new Date(isoStr);
    if (Number.isNaN(d.getTime())) return "—";
    s = d.toISOString();
  } else if (typeof isoStr !== "string") {
    return "—";
  } else {
    s = String(isoStr).trim();
  }
  if (!s) return "—";
  const isoMatch = s.match(/^(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2}):(\d{2})/);
  if (isoMatch) {
    const [, y, m, day, h, min, sec] = isoMatch;
    return `${y}/${m}/${day} ${h}:${min}:${sec}`;
  }
  try {
    const hasTz = /[Zz]$|[+-]\d{2}:?\d{2}$/.test(s);
    const toParse = hasTz ? s : s.includes("T") ? s + "Z" : s.replace(" ", "T") + "Z";
    const d = new Date(toParse);
    if (Number.isNaN(d.getTime())) return s;
    const bj = new Date(d.getTime() + 8 * 60 * 60 * 1000);
    const y = bj.getUTCFullYear();
    const m = String(bj.getUTCMonth() + 1).padStart(2, "0");
    const day = String(bj.getUTCDate()).padStart(2, "0");
    const h = String(bj.getUTCHours()).padStart(2, "0");
    const min = String(bj.getUTCMinutes()).padStart(2, "0");
    const sec = String(bj.getUTCSeconds()).padStart(2, "0");
    if ([y, m, day, h, min, sec].some((v) => Number.isNaN(Number(v)))) return s;
    const out = `${y}/${m}/${day} ${h}:${min}:${sec}`;
    return out.includes("NaN") ? s : out;
  } catch {
    return s;
  }
}

function getErrorMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  if (typeof e === "object" && e && "response" in e) {
    const ax = e as { response?: { data?: { message?: string; detail?: string } } };
    const data = ax.response?.data;
    if (data?.detail) return typeof data.detail === "string" ? data.detail : String(data.detail);
    return data?.message ?? "请求失败";
  }
  return "请求失败";
}

watch(typeVal, () => {
  if (!loading.value) handleTest();
}, { immediate: true });

async function handleTest() {
  loading.value = true;
  result.value = null;
  loadingInstance = ElLoading.service({
    lock: true,
    text: "请求新浪财经 news API...",
    background: "rgba(0,0,0,0.4)",
  });
  try {
    const res = (await sinaTest({
      category: typeVal.value,
      limit: limitVal.value,
      save_to_db: saveToDb.value,
    })) as { data?: Record<string, unknown> };
    result.value = res?.data ?? null;
    ElMessage.success("请求成功");
  } catch (e) {
    const msg = getErrorMessage(e);
    ElMessage.error(msg);
  } finally {
    loadingInstance?.close();
    loadingInstance = null;
    loading.value = false;
  }
}
</script>

<template>
  <div class="sina-test">
    <!-- 二级 Tab 点击自动发起测试，也可点击「发起测试」按钮 -->
    <ElTabs v-model="typeVal" type="card" class="tabs-level-2">
      <ElTabPane
        v-for="opt in typeOptions"
        :key="opt.value"
        :name="opt.value"
        :label="opt.label"
      />
    </ElTabs>
    <ElDivider class="form-divider" />
    <ElForm label-position="top" class="form-row" @submit.prevent>
      <ElFormItem label="Limit">
        <ElInputNumber v-model="limitVal" :min="1" :max="100" style="width: 120px" />
      </ElFormItem>
      <ElFormItem label="保存到数据库">
        <ElSwitch v-model="saveToDb" />
      </ElFormItem>
      <ElFormItem label=" ">
        <ElButton type="primary" native-type="button" :loading="loading" @click="handleTest">发起测试</ElButton>
      </ElFormItem>
    </ElForm>

    <ElCard v-if="showTimeline" class="timeline-card" shadow="never">
      <template #header>
        <span>时间线</span>
        <ElTag v-if="parsedList.length" size="small" type="info" class="count-tag">共 {{ parsedList.length }} 条</ElTag>
      </template>
      <ElTimeline>
        <ElTimelineItem
          v-for="(item, idx) in parsedList"
          :key="idx"
          :timestamp="formatBeijingTime(item.published_time)"
          placement="top"
        >
          <div class="timeline-content">
            <div class="timeline-title">{{ item.title }}</div>
            <p v-if="item.summary" class="timeline-summary">{{ item.summary }}</p>
            <ElLink
              v-if="item.url"
              :href="item.url"
              type="primary"
              target="_blank"
              rel="noopener"
              class="timeline-link"
            >
              原文链接
            </ElLink>
            <ElTooltip v-if="item.sentiment != null" placement="top" trigger="hover" popper-class="sentiment-tooltip-popper">
              <template #content>
                <div class="sentiment-tooltip">
                  <div><strong>情感分数</strong>：基于摘要的简单情感分析</div>
                  <div>正数表示偏多，负数表示偏空</div>
                  <div>范围 -1 ~ 1</div>
                  <div>score = (正面词 - 负面词) / 总词数，约 -1 ~ 1</div>
                </div>
              </template>
              <ElTag size="small" :type="item.sentiment >= 0 ? 'success' : 'danger'" class="sentiment-tag">
                情感 {{ item.sentiment }}
              </ElTag>
            </ElTooltip>
          </div>
        </ElTimelineItem>
      </ElTimeline>
    </ElCard>

    <ElCard v-else-if="parsedList.length > 0" class="fields-card" shadow="never">
      <template #header>字段列表</template>
      <div class="field-list">
        <div v-for="(item, idx) in parsedList" :key="idx" class="field-item">
          <div class="field-label">标题</div>
          <div class="field-value">{{ item.title }}</div>
          <div class="field-label">发布时间</div>
          <div class="field-value">{{ formatBeijingTime(item.published_time) }}</div>
          <div class="field-label">摘要</div>
          <div class="field-value field-summary">{{ item.summary || "—" }}</div>
          <div class="field-label">原文链接</div>
          <div class="field-value">
            <ElLink v-if="item.url" :href="item.url" type="primary" target="_blank" rel="noopener">打开</ElLink>
            <span v-else>—</span>
          </div>
        </div>
      </div>
    </ElCard>

    <ElCard v-if="result" class="result-card" shadow="never">
      <template #header>原始 JSON</template>
      <ElCollapse>
        <ElCollapseItem title="展开查看" name="raw">
          <pre class="json-pre"><code>{{ rawJson }}</code></pre>
        </ElCollapseItem>
      </ElCollapse>
    </ElCard>
  </div>
</template>

<style scoped>
.sina-test {
  padding: 0;
}

.tabs-level-2 :deep(.el-tabs__header) {
  margin: 0 0 16px;
  padding: 0;
  border: none;
  background: transparent;
}
.tabs-level-2 :deep(.el-tabs__nav-wrap) {
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
  padding: 2px 0;
}
.tabs-level-2 :deep(.el-tabs__nav) {
  border: none;
}
.tabs-level-2 :deep(.el-tabs__item) {
  font-size: 0.875rem;
  padding: 0 16px;
  height: 36px;
  line-height: 36px;
  border: 1px solid var(--el-border-color);
  border-right: none;
}
.tabs-level-2 :deep(.el-tabs__item:first-child) {
  border-radius: 4px 0 0 4px;
}
.tabs-level-2 :deep(.el-tabs__item:last-child) {
  border-right: 1px solid var(--el-border-color);
  border-radius: 0 4px 4px 0;
}
.tabs-level-2 :deep(.el-tabs__item.is-active) {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  border-color: var(--el-color-primary);
  font-weight: 500;
}
.tabs-level-2 :deep(.el-tabs__item.is-active + .el-tabs__item) {
  border-left-color: var(--el-border-color);
}
html.dark .tabs-level-2 :deep(.el-tabs__item.is-active) {
  background: var(--el-color-primary-dark-2);
  color: var(--el-color-primary-light-3);
}
.tabs-level-2 :deep(.el-tabs__content) {
  padding: 0;
}
.tabs-level-2 :deep(.el-tabs__active-bar) {
  display: none;
}
.tabs-level-2 :deep(.el-tabs__indicators) {
  display: none;
}

.form-divider {
  margin: 16px 0;
}

.form-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 16px;
}

.form-row :deep(.el-form-item) {
  margin-bottom: 0;
}

.timeline-card,
.fields-card,
.result-card {
  margin-top: 20px;
}

.count-tag {
  margin-left: 8px;
}

.timeline-content {
  padding: 4px 0;
}

.timeline-title {
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin-bottom: 6px;
}

.timeline-summary {
  margin: 0 0 8px;
  font-size: 0.9rem;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

.timeline-link {
  margin-right: 8px;
}

.sentiment-tag {
  vertical-align: middle;
}

:deep(.sentiment-tooltip-popper .sentiment-tooltip) {
  max-width: 320px;
  line-height: 1.6;
}
:deep(.sentiment-tooltip-popper .sentiment-tooltip div) {
  margin-bottom: 4px;
}
:deep(.sentiment-tooltip-popper .sentiment-tooltip div:last-child) {
  margin-bottom: 0;
}

.field-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field-item {
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
}

.field-label {
  font-size: 0.8rem;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}

.field-value {
  font-size: 0.95rem;
  color: var(--el-text-color-primary);
  margin-bottom: 8px;
}

.field-value:last-child,
.field-summary {
  margin-bottom: 0;
}

.field-summary {
  max-height: 80px;
  overflow-y: auto;
}

.json-pre {
  margin: 0;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  font-size: 12px;
  font-family: ui-monospace, monospace;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--el-text-color-primary);
}

@media (max-width: 480px) {
  .form-row :deep(.el-input-number) {
    width: 100% !important;
    max-width: none;
  }

  .timeline-card :deep(.el-timeline-item__timestamp) {
    font-size: 0.8rem;
  }

  .field-item {
    padding: 10px;
  }
}
</style>
