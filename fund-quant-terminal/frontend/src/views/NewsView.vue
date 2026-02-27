<!--
  =====================================================
  市场资讯 - 响应式卡片网格 + 无限滚动 + 60s 自动刷新 + 收藏 + 骨架屏
  =====================================================
-->
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import * as echarts from "echarts";
import {
  ElCard,
  ElTable,
  ElTableColumn,
  ElRow,
  ElCol,
  ElInput,
  ElDatePicker,
  ElButton,
  ElMessage,
  ElEmpty,
  ElTag,
  ElDialog,
  ElSkeleton,
  ElCheckbox,
  ElTooltip,
} from "element-plus";
import { Search, RefreshRight, Star, StarFilled } from "@element-plus/icons-vue";
import { getNewsList, getSentimentTrend, batchGrok } from "../api/news";
import type { NewsItem, SentimentTrendItem } from "../api/news";
import { fetchGrokDecision } from "../api/grok";
import { useChartResize } from "../composables/useChartResize";

const SUMMARY_MAX = 120;
const FAVORITES_KEY = "news_favorites";
const REFRESH_INTERVAL = 60000;

function truncate(str: string | undefined, max: number): string {
  if (!str) return "";
  return str.length <= max ? str : str.slice(0, max) + "…";
}

function loadFavorites(): Set<string> {
  try {
    const raw = localStorage.getItem(FAVORITES_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as string[];
    return new Set(Array.isArray(arr) ? arr : []);
  } catch {
    return new Set();
  }
}

function saveFavorites(set: Set<string>) {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify([...set]));
}

const favorites = ref<Set<string>>(loadFavorites());

function toggleFavorite(link: string | undefined) {
  if (!link) return;
  const next = new Set(favorites.value);
  if (next.has(link)) {
    next.delete(link);
    ElMessage.success("已取消收藏");
  } else {
    next.add(link);
    ElMessage.success("已收藏");
  }
  favorites.value = next;
  saveFavorites(next);
}

function isFavorited(link: string | undefined) {
  return link ? favorites.value.has(link) : false;
}

const loading = ref(false);
const loadMoreLoading = ref(false);
const newsList = ref<NewsItem[]>([]);
const total = ref(0);
const page = ref(1);
const limit = ref(20);
const sentimentSummary = ref<{ positive: number; neutral: number; negative: number; avg: number } | null>(null);

function sentimentTagType(score: number | undefined | null): "success" | "info" | "danger" {
  if (score == null) return "info";
  if (score > 0.3) return "success";
  if (score < -0.3) return "danger";
  return "info";
}
const fundCode = ref("");
const days = ref(7);
const searchText = ref("");
const dateRange = ref<[Date, Date] | string[] | null>(null);

const router = useRouter();
const selectedRows = ref<NewsItem[]>([]);
const viewMode = ref<"cards" | "table">("cards");
let refreshTimer: ReturnType<typeof setInterval> | null = null;

// 情绪趋势图
const sentimentChartRef = ref<HTMLElement | null>(null);
const tableRef = ref<InstanceType<typeof ElTable> | null>(null);
const sentimentTrendItems = ref<SentimentTrendItem[]>([]);
let sentimentChartInstance: echarts.ECharts | null = null;

useChartResize(sentimentChartRef, () => sentimentChartInstance);

async function loadSentimentTrend() {
  const fc = fundCode.value.trim();
  if (!fc) {
    sentimentTrendItems.value = [];
    return;
  }
  try {
    const res = (await getSentimentTrend({ fund_code: fc, days: Math.min(days.value, 30) })) as {
      data?: { items?: SentimentTrendItem[] };
    };
    sentimentTrendItems.value = res?.data?.items ?? [];
    await nextTick();
    renderSentimentChart();
  } catch {
    sentimentTrendItems.value = [];
  }
}

function renderSentimentChart() {
  if (!sentimentChartRef.value) return;
  const items = sentimentTrendItems.value;
  if (!sentimentChartInstance) sentimentChartInstance = echarts.init(sentimentChartRef.value);
  const dates = items.map((i) => i.date);
  const values = items.map((i) => i.avg_sentiment);
  sentimentChartInstance.setOption({
    tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
    grid: { left: "3%", right: "4%", bottom: "3%", top: "10%", containLabel: true },
    xAxis: { type: "category", data: dates, boundaryGap: false },
    yAxis: {
      type: "value",
      min: -1,
      max: 1,
      splitLine: { lineStyle: { type: "dashed", opacity: 0.3 } },
      axisLabel: { formatter: "{value}" },
    },
    series: [{ name: "日均情绪", type: "line", smooth: true, data: values, symbol: "circle", symbolSize: 6 }],
  });
}

watch(fundCode, (fc) => {
  if (fc?.trim()) loadSentimentTrend();
  else sentimentTrendItems.value = [];
}, { immediate: false });

// Grok 决策弹窗
const grokDialogVisible = ref(false);
const grokLoading = ref(false);
const grokPrompt = ref("");
const grokNewsSummary = ref<{ title: string; link: string; pub_date: string }[]>([]);
const grokSourceFundCode = ref("");

function onSelectionChange(rows: NewsItem[]) {
  selectedRows.value = rows;
}

async function openGrokDialog(mode: "fund" | "global" | "selected") {
  grokDialogVisible.value = true;
  grokPrompt.value = "";
  grokNewsSummary.value = [];
  grokSourceFundCode.value = mode === "fund" ? fundCode.value.trim() : "";
  grokLoading.value = true;
  try {
    let res;
    if (mode === "selected" && selectedRows.value.length > 0) {
      const links = selectedRows.value.map((r) => r.link).filter(Boolean) as string[];
      res = await batchGrok(links);
    } else if (mode === "fund" && fundCode.value.trim()) {
      res = await fetchGrokDecision({ fund_code: fundCode.value.trim(), include_news: true });
    } else {
      res = await fetchGrokDecision({ fund_code: "", include_news: true });
    }
    const d = (res as { data?: { prompt?: string; news_summary?: { title: string; link: string; pub_date: string }[] } })?.data;
    grokPrompt.value = d?.prompt ?? "";
    grokNewsSummary.value = d?.news_summary ?? [];
  } catch {
    grokPrompt.value = "";
    grokNewsSummary.value = [];
  } finally {
    grokLoading.value = false;
  }
}

async function openBatchGrokDialog() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning("请先勾选新闻");
    return;
  }
  openGrokDialog("selected");
}

function clearSelection() {
  selectedRows.value = [];
  tableRef.value?.clearSelection?.();
}

function canGenerateBySelected() {
  return selectedRows.value.length > 0;
}

function canGenerateByFund() {
  return !!fundCode.value.trim();
}

function copyGrokPrompt() {
  if (!grokPrompt.value) {
    ElMessage.warning("暂无提示词可复制");
    return;
  }
  navigator.clipboard.writeText(grokPrompt.value).then(
    () => ElMessage.success("已复制到剪贴板"),
    () => ElMessage.error("复制失败")
  );
}

function saveAsDecision() {
  if (!grokPrompt.value) return;
  sessionStorage.setItem(
    "grokPromptFromNews",
    JSON.stringify({ grok_prompt: grokPrompt.value, fund_code: grokSourceFundCode.value })
  );
  grokDialogVisible.value = false;
  router.push({ name: "DecisionLog" });
  ElMessage.success("已跳转到决策页面，请填写并提交");
}

const filteredList = computed(() => {
  let list = newsList.value;
  if (dateRange.value && dateRange.value.length === 2) {
    const [start, end] = dateRange.value;
    const startStr = typeof start === "string" ? start.slice(0, 10) : (start as Date).toISOString?.().slice(0, 10) ?? "";
    const endStr = typeof end === "string" ? end.slice(0, 10) : (end as Date).toISOString?.().slice(0, 10) ?? "";
    list = list.filter((item) => {
      const d = (item.pub_date || item.created_at || "").toString().slice(0, 10);
      return d >= startStr && d <= endStr;
    });
  }
  return list;
});

const hasMore = computed(() => filteredList.value.length < total.value);

async function loadNews(p = 1, append = false, opts?: { skipLoading?: boolean }) {
  if (loading.value && !append) return;
  if (append && loadMoreLoading.value) return;
  if (append) {
    loadMoreLoading.value = true;
  } else {
    loading.value = true;
  }
  try {
    const res = (await getNewsList(
      {
        fund_code: fundCode.value.trim() || undefined,
        days: days.value,
        keyword: searchText.value.trim() || undefined,
        page: p,
        limit: limit.value,
        refresh: false,
      },
      { skipLoading: opts?.skipLoading }
    )) as { data?: { items?: NewsItem[]; total?: number; page?: number; limit?: number; sentiment_summary?: typeof sentimentSummary.value } };
    const d = res?.data;
    const items = Array.isArray(d?.items) ? d.items : [];
    if (append) {
      const existingLinks = new Set(newsList.value.map((n) => n.link));
      const newItems = items.filter((it) => !existingLinks.has(it.link));
      newsList.value = [...newsList.value, ...newItems];
    } else {
      newsList.value = items;
    }
    total.value = d?.total ?? 0;
    page.value = d?.page ?? p;
    if (d?.sentiment_summary) sentimentSummary.value = d.sentiment_summary;
    if (!append && newsList.value.length > 0) {
      ElMessage.success(`共 ${total.value} 条`);
    } else if (!append && newsList.value.length === 0) {
      ElMessage.warning("暂无数据，可尝试 RSS 抓取");
    }
  } catch (e) {
    if (!opts?.skipLoading) {
      console.error(e);
      ElMessage.error("加载失败");
      newsList.value = [];
      total.value = 0;
      sentimentSummary.value = null;
    }
  } finally {
    loading.value = false;
    loadMoreLoading.value = false;
  }
}

function loadMore() {
  if (!hasMore.value || loading.value || loadMoreLoading.value) return;
  loadNews(page.value + 1, true);
}

async function loadWithRefresh() {
  if (loading.value) return;
  loading.value = true;
  try {
    const res = (await getNewsList({
      fund_code: fundCode.value.trim() || undefined,
      days: days.value,
      keyword: searchText.value.trim() || undefined,
      page: 1,
      limit: limit.value,
      refresh: true,
    })) as { data?: { items?: NewsItem[]; total?: number; sentiment_summary?: typeof sentimentSummary.value } };
    const d = res?.data;
    newsList.value = Array.isArray(d?.items) ? d.items : [];
    total.value = d?.total ?? 0;
    page.value = 1;
    sentimentSummary.value = d?.sentiment_summary ?? null;
    ElMessage.success(`共 ${total.value} 条`);
  } catch (e) {
    console.error(e);
    ElMessage.error("抓取失败");
  } finally {
    loading.value = false;
  }
}

function doQuery() {
  page.value = 1;
  loadNews(1);
  if (fundCode.value.trim()) loadSentimentTrend();
}

function toggleCardSelection(item: NewsItem, checked: boolean) {
  if (checked) {
    if (!selectedRows.value.some((r) => r.link === item.link)) {
      selectedRows.value = [...selectedRows.value, item];
    }
  } else {
    selectedRows.value = selectedRows.value.filter((r) => r.link !== item.link);
  }
}

function isCardSelected(item: NewsItem) {
  return selectedRows.value.some((r) => r.link === item.link);
}

onMounted(() => {
  loadNews(1);
  refreshTimer = setInterval(() => {
    loadNews(page.value, false, { skipLoading: true });
  }, REFRESH_INTERVAL);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<template>
  <div class="news-view">
    <h2 class="page-title">市场资讯</h2>

    <div v-if="sentimentSummary && (newsList.length > 0)" class="sentiment-summary">
      <span class="summary-label">情绪汇总 (本页)</span>
      <ElTag type="success" size="small">看涨 {{ sentimentSummary.positive }}</ElTag>
      <ElTag type="info" size="small">中性 {{ sentimentSummary.neutral }}</ElTag>
      <ElTag type="danger" size="small">看跌 {{ sentimentSummary.negative }}</ElTag>
      <span class="avg-sentiment">平均 {{ sentimentSummary.avg }}</span>
      <span class="refresh-hint">60s 自动刷新</span>
    </div>

    <ElCard shadow="never" class="filter-card">
      <div class="filter-row">
        <ElInput
          v-model="searchText"
          placeholder="搜索标题、摘要、来源、基金代码"
          clearable
          class="filter-input"
          :prefix-icon="Search"
        />
        <ElDatePicker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          format="YYYY-MM-DD"
          clearable
          class="filter-daterange"
        />
        <ElInput
          v-model="fundCode"
          placeholder="基金代码"
          clearable
          class="filter-fund"
        />
        <ElInput
          v-model.number="days"
          type="number"
          placeholder="天数"
          min="1"
          max="30"
          class="filter-days"
        />
        <ElButton type="primary" :loading="loading" @click="doQuery">
          查询
        </ElButton>
        <ElButton :icon="RefreshRight" :loading="loading" @click="loadWithRefresh">
          RSS 抓取
        </ElButton>
        <ElButton type="success" :loading="grokLoading" @click="openGrokDialog(canGenerateBySelected() ? 'selected' : canGenerateByFund() ? 'fund' : 'global')">
          生成 Grok 决策
        </ElButton>
        <ElButton :type="viewMode === 'cards' ? 'primary' : undefined" size="small" @click="viewMode = 'cards'">卡片</ElButton>
        <ElButton :type="viewMode === 'table' ? 'primary' : undefined" size="small" @click="viewMode = 'table'">表格</ElButton>
      </div>
    </ElCard>

    <!-- 批量选中 → 生成综合 Grok 决策 -->
    <div v-if="selectedRows.length > 0" class="batch-grok-bar">
      <span class="batch-label">已选 {{ selectedRows.length }} 条新闻</span>
      <ElButton type="success" :loading="grokLoading" @click="openBatchGrokDialog">
        批量生成综合 Grok 决策
      </ElButton>
      <ElButton size="small" @click="clearSelection">取消选择</ElButton>
    </div>

    <!-- 情绪趋势图（选中基金时显示） -->
    <ElCard v-if="fundCode.trim()" shadow="never" class="chart-card">
      <template #header>
        <span>基金 {{ fundCode }} 情绪趋势（日均）</span>
      </template>
      <div v-if="sentimentTrendItems.length > 0" ref="sentimentChartRef" class="sentiment-chart" />
      <ElEmpty v-else description="暂无趋势数据" class="chart-empty" />
    </ElCard>

    <!-- 骨架屏：初次加载 -->
    <div v-if="loading && newsList.length === 0" class="skeleton-wrap">
      <ElRow :gutter="16">
        <ElCol v-for="i in 6" :key="i" :xs="24" :sm="12" :md="8" :lg="6">
          <ElCard shadow="never" class="news-card">
            <ElSkeleton :rows="4" animated />
          </ElCard>
        </ElCol>
      </ElRow>
    </div>

    <!-- 响应式卡片网格 -->
    <ElRow v-else-if="filteredList.length > 0 && viewMode === 'cards'" :gutter="16" class="cards-row">
      <ElCol v-for="item in filteredList" :key="item.link || item.title" :xs="24" :sm="12" :md="8" :lg="6">
        <ElCard shadow="hover" class="news-card" :body-style="{ padding: '12px 14px' }">
          <div class="news-card-header">
            <ElCheckbox
              :model-value="isCardSelected(item)"
              @change="(v) => toggleCardSelection(item, v === true)"
            />
            <ElTooltip :content="isFavorited(item.link) ? '取消收藏' : '收藏'" placement="top">
              <ElButton
                :icon="isFavorited(item.link) ? StarFilled : Star"
                link
                :type="isFavorited(item.link) ? 'warning' : 'info'"
                size="small"
                @click="toggleFavorite(item.link)"
              />
            </ElTooltip>
          </div>
          <a
            v-if="item.link"
            :href="item.link"
            target="_blank"
            rel="noopener"
            class="news-title"
          >{{ item.title || "(无标题)" }}</a>
          <span v-else class="news-title-text">{{ item.title || "(无标题)" }}</span>
          <div class="news-meta">
            <span class="news-date">{{ (item.pub_date || item.created_at || "-").toString().slice(0, 16) }}</span>
            <ElTag v-if="item.source" size="small" type="info">{{ item.source }}</ElTag>
            <ElTag v-if="item.fund_code" size="small" type="primary">{{ item.fund_code }}</ElTag>
          </div>
          <p class="news-summary">{{ truncate(item.content_summary, SUMMARY_MAX) }}</p>
          <div class="news-footer">
            <ElTag
              v-if="item.sentiment_score != null"
              :type="sentimentTagType(item.sentiment_score)"
              size="small"
            >
              情绪 {{ item.sentiment_score }}
            </ElTag>
            <span v-else class="sentiment-placeholder">-</span>
          </div>
        </ElCard>
      </ElCol>
    </ElRow>

    <!-- 表格视图 -->
    <ElCard v-else-if="filteredList.length > 0 && viewMode === 'table'" shadow="never" class="table-card">
      <ElTable
        ref="tableRef"
        :data="filteredList"
        stripe
        :header-cell-style="{ background: 'var(--el-fill-color-light)' }"
        @selection-change="onSelectionChange"
      >
        <ElTableColumn type="selection" width="48" />
        <ElTableColumn prop="title" label="标题" min-width="280">
          <template #default="{ row }">
            <a v-if="row.link" :href="row.link" target="_blank" rel="noopener" class="title-link">{{ row.title || "(无标题)" }}</a>
            <span v-else class="title-text">{{ row.title || "(无标题)" }}</span>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="pub_date" label="发布日期" width="110">
          <template #default="{ row }">{{ (row.pub_date || row.created_at || "-").toString().slice(0, 16) }}</template>
        </ElTableColumn>
        <ElTableColumn prop="source" label="来源" width="100">
          <template #default="{ row }"><ElTag size="small" type="info">{{ row.source || "RSS" }}</ElTag></template>
        </ElTableColumn>
        <ElTableColumn prop="fund_code" label="基金" width="90">
          <template #default="{ row }">
            <ElTag v-if="row.fund_code" size="small" type="primary">{{ row.fund_code }}</ElTag>
            <span v-else>-</span>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="content_summary" label="摘要" min-width="200">
          <template #default="{ row }"><span class="summary-cell">{{ truncate(row.content_summary, SUMMARY_MAX) }}</span></template>
        </ElTableColumn>
        <ElTableColumn prop="sentiment_score" label="情绪" width="80" align="center">
          <template #default="{ row }">
            <ElTag v-if="row.sentiment_score != null" :type="sentimentTagType(row.sentiment_score)" size="small">{{ row.sentiment_score }}</ElTag>
            <span v-else>-</span>
          </template>
        </ElTableColumn>
        <ElTableColumn label="收藏" width="64" align="center">
          <template #default="{ row }">
            <ElButton
              :icon="isFavorited(row.link) ? StarFilled : Star"
              link
              :type="isFavorited(row.link) ? 'warning' : 'info'"
              size="small"
              @click="toggleFavorite(row.link)"
            />
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>

    <!-- 加载更多 -->
    <div v-if="hasMore && !loading && filteredList.length > 0" class="load-more-row">
      <ElButton :loading="loadMoreLoading" @click="loadMore">
        加载更多 ({{ filteredList.length }}/{{ total }})
      </ElButton>
    </div>

    <ElEmpty
      v-if="!loading && filteredList.length === 0"
      description="暂无新闻数据"
      class="table-empty"
    />

    <ElDialog
      v-model="grokDialogVisible"
      title="Grok 决策提示词"
      width="700px"
      class="grok-dialog"
      destroy-on-close
    >
      <div v-loading="grokLoading" class="grok-dialog-body">
        <div v-if="grokPrompt" class="grok-prompt-wrap">
          <ElInput
            :model-value="grokPrompt"
            type="textarea"
            :rows="12"
            readonly
            class="grok-textarea"
          />
        </div>
        <p v-else-if="!grokLoading" class="grok-empty">暂无数据</p>
      </div>
      <template #footer>
        <ElButton @click="grokDialogVisible = false">关闭</ElButton>
        <ElButton type="primary" :disabled="!grokPrompt" @click="copyGrokPrompt">
          复制到剪贴板
        </ElButton>
        <ElButton type="success" :disabled="!grokPrompt" @click="saveAsDecision">
          保存为决策
        </ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.news-view {
  max-width: 1200px;
}

.page-title {
  margin: 0 0 12px;
  color: var(--el-text-color-primary);
}

.sentiment-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 10px 14px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  font-size: 13px;
}

.sentiment-summary .summary-label {
  color: var(--el-text-color-secondary);
  margin-right: 4px;
}

.sentiment-summary .avg-sentiment {
  color: var(--el-text-color-regular);
  margin-left: 8px;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.filter-input { width: 200px; min-width: 120px; }
.filter-daterange { width: 240px; min-width: 180px; }
.filter-fund { width: 90px; }
.filter-days { width: 72px; }
@media (max-width: 768px) {
  .filter-input { width: 100%; }
  .filter-daterange { width: 100%; }
}

.refresh-hint {
  margin-left: auto;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.batch-grok-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 16px;
  background: var(--el-color-success-light-9);
  border-radius: 8px;
  border: 1px solid var(--el-color-success-light-5);
}

.batch-grok-bar .batch-label {
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.chart-card {
  margin-bottom: 20px;
}

.sentiment-chart {
  width: 100%;
  height: 220px;
}

.chart-empty {
  padding: 24px;
}

.skeleton-wrap {
  margin-bottom: 16px;
}

.cards-row {
  margin-bottom: 16px;
}

.news-card {
  height: 100%;
  background: var(--el-bg-color);
  border-color: var(--el-border-color-lighter);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.news-card:hover {
  border-color: var(--el-border-color);
}

.news-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.news-title {
  display: block;
  font-weight: 500;
  color: var(--el-color-primary);
  text-decoration: none;
  margin-bottom: 6px;
  line-height: 1.4;
}

.news-title:hover {
  text-decoration: underline;
}

.news-title-text {
  display: block;
  color: var(--el-text-color-primary);
  margin-bottom: 6px;
}

.news-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.news-date {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.news-summary {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
  margin: 0 0 8px;
}

.news-footer {
  padding-top: 4px;
}

.sentiment-placeholder {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.load-more-row {
  display: flex;
  justify-content: center;
  padding: 20px;
}

.table-card {
  margin-top: 0;
  background: var(--el-bg-color);
}

.title-link {
  color: var(--el-color-primary);
  text-decoration: none;
}

.title-link:hover {
  text-decoration: underline;
}

.title-text {
  color: var(--el-text-color-primary);
}

.summary-cell {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.4;
}

.table-empty {
  padding: 40px 0;
}

.pagination-row {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.grok-dialog-body {
  min-height: 120px;
}

.grok-prompt-wrap {
  margin-bottom: 8px;
}

.grok-textarea {
  font-family: var(--el-font-family-mono, monospace);
  font-size: 13px;
}

.grok-empty {
  color: var(--el-text-color-secondary);
  text-align: center;
  padding: 24px;
}

/* 深色模式：表格与卡片 */
:deep(.el-table) {
  --el-table-bg-color: var(--el-bg-color);
  --el-table-tr-bg-color: var(--el-bg-color);
  --el-table-header-bg-color: var(--el-fill-color-light);
  --el-table-border-color: var(--el-border-color-lighter);
}

html.dark .news-card {
  --el-card-bg-color: var(--el-bg-color);
}

/* 骨架屏深色 */
html.dark .news-card .el-skeleton__item {
  background: linear-gradient(90deg, var(--el-fill-color) 25%, var(--el-fill-color-light) 37%, var(--el-fill-color) 63%);
}
</style>
