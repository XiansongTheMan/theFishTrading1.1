# -*- coding: utf-8 -*-
"""修复金融 Tab channel 并恢复中文编码"""
import os

path = os.path.join(os.path.dirname(__file__), "src", "views", "WallstreetTestView.vue")

content = '''<!--
  华尔街见闻接口测试 - Card + 深色模式，与资产曲线页规范一致
-->
<script setup lang="ts">
import { ref, computed } from "vue";
import {
  ElCard,
  ElTabs,
  ElTabPane,
  ElInput,
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
import { wallstreetcnTest, type WallStreetCNType } from "@/news/api/wallstreet";

interface ParsedItem {
  title: string;
  published_time: string | null;
  summary: string;
  url: string | null;
  sentiment?: number;
}

interface SourceOption {
  value: string;
  label: string;
}

interface TypeOption {
  value: string;
  label: string;
  type: WallStreetCNType;
  channel?: string;
}

const sourceOptions: SourceOption[] = [
  { value: "wallstreetcn", label: "华尔街见闻" },
];

const sourceVal = ref("wallstreetcn");

const typeOptions: TypeOption[] = [
  { value: "lives:global-channel", label: "实时快讯", type: "lives", channel: "global-channel" },
  { value: "lives:a-stock-channel", label: "A股", type: "lives", channel: "a-stock-channel" },
  { value: "lives:goldc-channel", label: "黄金", type: "lives", channel: "goldc-channel" },
  { value: "lives:us-stock-channel", label: "美股", type: "lives", channel: "us-stock-channel" },
  { value: "lives:tech-channel", label: "科技", type: "lives", channel: "tech-channel" },
  { value: "lives:finance-bonds", label: "金融", type: "lives", channel: "bond-channel" },
  { value: "lives:oil-channel", label: "石油", type: "lives", channel: "oil-channel" },
  { value: "lives:bond-channel", label: "债券", type: "lives", channel: "bond-channel" },
  { value: "lives:forex-fx", label: "外汇", type: "lives", channel: "forex-channel" },
  { value: "lives:commodity-channel", label: "大宗", type: "lives", channel: "commodity-channel" },
  { value: "lives:hk-stock-channel", label: "港股", type: "lives", channel: "hk-stock-channel" },
  { value: "keyword", label: "关键词搜索", type: "keyword" },
];

const typeVal = ref("lives:global-channel");
const keywordVal = ref("");
const limitVal = ref(10);
const saveToDb = ref(false);
const loading = ref(false);
const result = ref<Record<string, unknown> | null>(null);
let loadingInstance: LoadingInstance | null = null;

const currentOpt = computed(() => typeOptions.find((t) => t.value === typeVal.value) ?? typeOptions[0]);
const needKeyword = computed(() => currentOpt.value.type === "keyword");

const parsedList = computed<ParsedItem[]>(() => {
  const r = result.value as { parsed?: ParsedItem[] } | null;
  return r?.parsed ?? [];
});

const showTimeline = computed(
  () => parsedList.value.length > 0 && currentOpt.value.type === "lives"
);

const rawJson = computed(() => {
  if (!result.value) return "";
  try {
    return JSON.stringify(result.value, null, 2);
  } catch {
    return String(result.value);
  }
});

/** 将 UTC ISO 时间转为北京时间 yyyy/mm/dd hh:mm:ss */
function formatBeijingTime(isoStr: string | null | undefined): string {
  if (!isoStr) return "\u2014";
  try {
    const d = new Date(isoStr.endsWith("Z") ? isoStr : isoStr + "Z");
    const bj = new Date(d.getTime() + 8 * 60 * 60 * 1000);
    const y = bj.getUTCFullYear();
    const m = String(bj.getUTCMonth() + 1).padStart(2, "0");
    const day = String(bj.getUTCDate()).padStart(2, "0");
    const h = String(bj.getUTCHours()).padStart(2, "0");
    const min = String(bj.getUTCMinutes()).padStart(2, "0");
    const s = String(bj.getUTCSeconds()).padStart(2, "0");
    return `${y}/${m}/${day} ${h}:${min}:${s}`;
  } catch {
    return isoStr;
  }
}

function getErrorMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  if (typeof e === "object" && e && "response" in e) {
    const ax = e as { response?: { data?: { message?: string } } };
    return ax.response?.data?.message ?? "请求失败";
  }
  return "请求失败";
}

function onSourceChange() {
  handleTest();
}

async function handleTest() {
  if (needKeyword.value && !keywordVal.value.trim()) {
    ElMessage.warning("请填写关键词");
    return;
  }
  loading.value = true;
  result.value = null;
  loadingInstance = ElLoading.service({ lock: true, text: "正在请求华尔街见闻 API...", background: "rgba(0,0,0,0.4)" });
  try {
    const opt = currentOpt.value;
    const res = (await wallstreetcnTest({
      type: opt.type,
      channel: opt.channel,
      keyword: keywordVal.value.trim() || undefined,
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
  <div class="wallstreet-test">
    <h2 class="page-title">news接口测试</h2>
    <ElCard shadow="never">
      <ElTabs v-model="sourceVal" type="border-card" @tab-change="onSourceChange" class="source-tabs">
        <ElTabPane
          v-for="src in sourceOptions"
          :key="src.value"
          :name="src.value"
          :label="src.label"
        >
          <ElTabs v-model="typeVal" type="card" @tab-change="handleTest" class="type-tabs">
            <ElTabPane
              v-for="opt in typeOptions"
              :key="opt.value"
              :name="opt.value"
              :label="opt.label"
            />
          </ElTabs>
          <ElForm label-position="top" class="form-row">
        <ElFormItem v-if="needKeyword" label="关键词">
          <ElInput v-model="keywordVal" placeholder="输入搜索词" style="width: 180px" clearable />
        </ElFormItem>
        <ElFormItem label="Limit">
          <ElInputNumber v-model="limitVal" :min="1" :max="100" style="width: 120px" />
        </ElFormItem>
        <ElFormItem label="保存至数据库">
          <ElSwitch v-model="saveToDb" />
        </ElFormItem>
        <ElFormItem label=" ">
          <ElButton type="primary" :loading="loading" @click="handleTest">执行测试</ElButton>
        </ElFormItem>
      </ElForm>
        </ElTabPane>
      </ElTabs>
    </ElCard>

    <!-- 时间线：lives 类型 -->
    <ElCard v-if="showTimeline" class="timeline-card" shadow="never">
      <template #header>
        <span>快讯时间线</span>
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
              查看原文
            </ElLink>
            <ElTooltip v-if="item.sentiment != null" placement="top" trigger="hover" popper-class="sentiment-tooltip-popper">
              <template #content>
                <div class="sentiment-tooltip">
                  <div><strong>本地关键词计算</strong>，非接口返回</div>
                  <div>正向词：利好、上涨、买入、大涨、看涨、反弹、增长、突破、增持、推荐</div>
                  <div>负向词：利空、下跌、卖出、大跌、看跌、回落、跌破、亏损、减持、预警</div>
                  <div>得分 = (正向次数 - 负向次数) / 总次数，范围 -1 ~ 1</div>
                </div>
              </template>
              <ElTag size="small" :type="item.sentiment >= 0 ? 'success' : 'danger'" class="sentiment-tag">
                情绪 {{ item.sentiment }}
              </ElTag>
            </ElTooltip>
          </div>
        </ElTimelineItem>
      </ElTimeline>
    </ElCard>

    <!-- 关键字段卡片：非 lives 但有 parsed 时 -->
    <ElCard
      v-else-if="parsedList.length > 0"
      class="fields-card"
      shadow="never"
    >
      <template #header>关键字段</template>
      <div class="field-list">
        <div v-for="(item, idx) in parsedList" :key="idx" class="field-item">
          <div class="field-label">标题</div>
          <div class="field-value">{{ item.title }}</div>
          <div class="field-label">发布时间</div>
          <div class="field-value">{{ formatBeijingTime(item.published_time) }}</div>
          <div class="field-label">摘要</div>
          <div class="field-value field-summary">{{ item.summary || "\u2014" }}</div>
          <div class="field-label">来源链接</div>
          <div class="field-value">
            <ElLink v-if="item.url" :href="item.url" type="primary" target="_blank" rel="noopener">打开链接</ElLink>
            <span v-else>\u2014</span>
          </div>
        </div>
      </div>
    </ElCard>

    <!-- 原始 JSON 折叠面板 -->
    <ElCard v-if="result" class="result-card" shadow="never">
      <template #header>原始 JSON</template>
      <ElCollapse>
        <ElCollapseItem title="查看完整响应" name="raw">
          <pre class="json-pre"><code>{{ rawJson }}</code></pre>
        </ElCollapseItem>
      </ElCollapse>
    </ElCard>
  </div>
</template>

<style scoped>
.wallstreet-test {
  max-width: 900px;
}

.page-title {
  margin: 0 0 20px;
}

.type-tabs {
  margin-bottom: 16px;
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

/* 情绪计算说明 tooltip */
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
  .form-row :deep(.el-select),
  .form-row :deep(.el-input),
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
'''

content = content.replace('\\u2014', '\u2014')

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done: 金融 Tab 已改为 bond-channel，并恢复中文编码")
