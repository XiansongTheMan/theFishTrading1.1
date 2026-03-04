<!--
  华尔街见闻接口测试 - Card + 深色模式，与资产曲线页规范一致
-->
<script setup lang="ts">
import { ref, computed } from "vue";
import {
  ElCard,
  ElSelect,
  ElOption,
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
  type LoadingInstance,
} from "element-plus";
import { wallstreetcnTest, type WallStreetCNType } from "../api/wallstreetcn";

interface ParsedItem {
  title: string;
  published_time: string | null;
  summary: string;
  url: string | null;
  sentiment?: number;
}

const typeOptions: { value: WallStreetCNType; label: string }[] = [
  { value: "lives", label: "实时快讯" },
  { value: "articles", label: "文章" },
  { value: "search", label: "个股搜索" },
  { value: "quote", label: "行情快照" },
  { value: "keyword", label: "关键词搜索" },
];

const typeVal = ref<WallStreetCNType>("lives");
const codeVal = ref("");
const keywordVal = ref("");
const limitVal = ref(10);
const saveToDb = ref(false);
const loading = ref(false);
const result = ref<Record<string, unknown> | null>(null);
let loadingInstance: LoadingInstance | null = null;

const needCode = computed(() => typeVal.value === "quote");
const needKeyword = computed(() => typeVal.value === "search" || typeVal.value === "keyword");

const parsedList = computed<ParsedItem[]>(() => {
  const r = result.value as { parsed?: ParsedItem[] } | null;
  return r?.parsed ?? [];
});

const showTimeline = computed(
  () => parsedList.value.length > 0 && (typeVal.value === "lives" || typeVal.value === "articles")
);

const rawJson = computed(() => {
  if (!result.value) return "";
  try {
    return JSON.stringify(result.value, null, 2);
  } catch {
    return String(result.value);
  }
});

function getErrorMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  if (typeof e === "object" && e && "response" in e) {
    const ax = e as { response?: { data?: { message?: string } } };
    return ax.response?.data?.message ?? "请求失败";
  }
  return "请求失败";
}

async function handleTest() {
  if (needCode.value && !codeVal.value.trim()) {
    ElMessage.warning("行情快照需填写股票代码");
    return;
  }
  if (needKeyword.value && !keywordVal.value.trim()) {
    ElMessage.warning("请填写关键词");
    return;
  }
  loading.value = true;
  result.value = null;
  loadingInstance = ElLoading.service({ lock: true, text: "正在请求华尔街见闻 API...", background: "rgba(0,0,0,0.4)" });
  try {
    const res = (await wallstreetcnTest({
      type: typeVal.value,
      code: codeVal.value.trim() || undefined,
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
    <h2 class="page-title">华尔街见闻股市情报测试菜单（供 Grok 决策参考）</h2>
    <ElCard shadow="never">
      <ElForm label-position="top" class="form-row">
        <ElFormItem label="接口类型">
          <ElSelect v-model="typeVal" placeholder="选择类型" style="width: 160px">
            <ElOption v-for="opt in typeOptions" :key="opt.value" :value="opt.value" :label="opt.label" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="needCode" label="股票代码">
          <ElInput v-model="codeVal" placeholder="如 600519" style="width: 140px" clearable />
        </ElFormItem>
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
    </ElCard>

    <!-- 时间线：lives / articles 类型 -->
    <ElCard v-if="showTimeline" class="timeline-card" shadow="never">
      <template #header>
        <span>快讯时间线</span>
        <ElTag v-if="parsedList.length" size="small" type="info" class="count-tag">共 {{ parsedList.length }} 条</ElTag>
      </template>
      <ElTimeline>
        <ElTimelineItem
          v-for="(item, idx) in parsedList"
          :key="idx"
          :timestamp="item.published_time || '—'"
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
            <ElTag v-if="item.sentiment != null" size="small" :type="item.sentiment >= 0 ? 'success' : 'danger'" class="sentiment-tag">
              情绪 {{ item.sentiment }}
            </ElTag>
          </div>
        </ElTimelineItem>
      </ElTimeline>
    </ElCard>

    <!-- 关键字段卡片：非 lives/articles 但有 parsed 时 -->
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
          <div class="field-value">{{ item.published_time || "—" }}</div>
          <div class="field-label">摘要</div>
          <div class="field-value field-summary">{{ item.summary || "—" }}</div>
          <div class="field-label">来源链接</div>
          <div class="field-value">
            <ElLink v-if="item.url" :href="item.url" type="primary" target="_blank" rel="noopener">打开链接</ElLink>
            <span v-else>—</span>
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
