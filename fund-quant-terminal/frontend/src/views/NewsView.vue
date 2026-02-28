<!--
  市场资讯 - 东方财富 + 新浪基金实时新闻
-->
<template>
  <div
    ref="pageRef"
    class="news-page"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
  >
    <div class="page-header">
      <h1 class="page-title">市场资讯</h1>
      <p class="page-desc">东方财富 + 新浪基金实时新闻</p>
    </div>

    <div class="toolbar toolbar-sticky">
      <el-select
        v-model="selectedFund"
        placeholder="选择基金"
        clearable
        style="width: 140px"
        @change="loadNews"
      >
        <el-option label="全部" value="全部" />
        <el-option v-for="f in fundOptions" :key="f" :label="f" :value="f" />
      </el-select>
      <el-button :icon="Refresh" :loading="loading" @click="loadNews">刷新</el-button>
      <span class="toolbar-hint">60s 自动刷新 · Ctrl+R 刷新 · Ctrl+K 搜索 · Ctrl+G Grok</span>
    </div>

    <div class="tabs-row">
      <el-tabs v-model="activeTab" class="news-tabs">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="我的收藏" name="favorites" />
      </el-tabs>
      <el-tag v-if="displayCount > 0" size="small" type="info" class="count-badge">
        共 {{ displayCount }} 条新闻
      </el-tag>
    </div>

    <div v-if="selectedLinks.length > 0" class="selection-bar">
      <span class="selection-count">已选择 {{ selectedLinks.length }} 条</span>
      <el-button type="success" :loading="grokLoading" @click="batchGenerateGrok">
        批量生成 Grok 决策
      </el-button>
      <el-button size="small" @click="clearSelection">取消选择</el-button>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-row :gutter="16" class="filter-row">
        <el-col :xs="24" :sm="12" :md="10">
          <el-input
            ref="searchInputRef"
            v-model="searchKeyword"
            placeholder="搜索标题或关键词 (Ctrl+K)"
            clearable
            size="default"
            class="search-input"
            @input="debouncedLoadNews"
          />
        </el-col>
        <el-col :xs="24" :sm="8" :md="6">
          <el-select
            v-model="sortBy"
            placeholder="排序"
            style="width: 100%"
            @change="loadNews"
          >
            <el-option label="发布时间↓" value="pub_date desc" />
            <el-option label="发布时间↑" value="pub_date asc" />
            <el-option label="情绪得分↓" value="sentiment desc" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="4" :md="8">
          <div class="filter-actions">
            <el-button :icon="Delete" @click="clearFilters">清空筛选</el-button>
            <el-button type="success" :loading="grokLoading" @click="generateGrokDecision">
              一键生成 Grok 决策
            </el-button>
            <el-dropdown trigger="click" @command="handleExport">
              <el-button type="primary" plain>导出<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="excel">导出 Excel</el-dropdown-item>
                  <el-dropdown-item command="pdf">导出 PDF</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <template v-if="loading">
      <el-row :gutter="20" class="news-grid skeleton-grid">
        <el-col v-for="i in 6" :key="i" :xs="24" :sm="12" :md="8">
          <el-card shadow="never" class="news-card skeleton-card">
            <template #header>
              <div class="card-header">
                <el-skeleton animated :rows="0">
                  <template #template>
                    <el-skeleton-item variant="text" style="width: 48px; height: 20px" />
                  </template>
                </el-skeleton>
                <el-skeleton animated :rows="0">
                  <template #template>
                    <el-skeleton-item variant="text" style="width: 60px; height: 16px; margin-left: auto" />
                  </template>
                </el-skeleton>
              </div>
            </template>
            <el-skeleton animated>
              <template #template>
                <el-skeleton-item variant="text" style="width: 90%; margin-bottom: 10px" />
                <el-skeleton-item variant="text" style="width: 70%" />
                <el-skeleton-item variant="text" style="width: 85%" />
                <el-skeleton-item variant="text" style="width: 50%" />
              </template>
            </el-skeleton>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <Transition name="news-fade" mode="out-in">
      <div v-else-if="displayList.length > 0" class="news-content" :key="activeTab">
        <el-row :gutter="20" class="news-grid">
          <el-col v-for="(item, idx) in displayList" :key="item.link || idx" :xs="24" :sm="12" :md="8">
          <el-card
            shadow="hover"
            class="news-card news-card-clickable"
            :class="{ 'news-card-selected': isSelected(item.link) }"
            @click="openDetail(item)"
          >
            <template #header>
              <div class="card-header">
                <el-checkbox
                  :model-value="isSelected(item.link)"
                  size="small"
                  @click.stop
                  @update:model-value="(v) => toggleSelect(item.link, v)"
                />
                <el-tag :type="sentimentType(item)" size="small">
                  {{ sentimentLabel(item) }}
                </el-tag>
                <span class="card-source">{{ item.source || "RSS" }}</span>
                <span class="card-date">{{ formatDate(item.pub_date || item.created_at) }}</span>
              </div>
            </template>
            <a :href="item.link" target="_blank" rel="noopener" class="news-title" @click.stop>
              {{ item.title || "(无标题)" }}
            </a>
            <p class="summary">{{ item.content_summary || item.summary || "" }}</p>
          </el-card>
        </el-col>
        </el-row>
        <div
          v-if="showInfiniteScroll"
          ref="sentinelRef"
          class="infinite-sentinel"
        />
        <div v-if="loadingMore" class="load-more">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载中...</span>
        </div>
      </div>

      <el-empty v-else class="empty-state" :key="activeTab">
        <template #image>
          <el-icon :size="80" color="var(--el-text-color-placeholder)">
            <Document />
          </el-icon>
        </template>
        <template #description>
          <span>{{ activeTab === "favorites" ? "暂无收藏" : "暂无匹配新闻" }}</span>
        </template>
        <el-button
          v-if="activeTab === 'favorites'"
          type="primary"
          @click="activeTab = 'all'"
        >
          去全部看看
        </el-button>
        <el-button v-else type="primary" :icon="Refresh" @click="loadNews">刷新</el-button>
      </el-empty>
    </Transition>

    <el-dialog
      v-model="detailDialogVisible"
      title="新闻详情"
      width="640px"
      class="news-detail-dialog"
      destroy-on-close
    >
      <template v-if="detailItem">
        <div class="detail-meta">
          <el-tag :type="detailItem ? sentimentType(detailItem) : 'info'" size="small">
            {{ detailItem ? sentimentLabel(detailItem) : "" }}
          </el-tag>
          <span class="detail-source">{{ detailItem.source || "RSS" }}</span>
          <span class="detail-date">{{ formatDate(detailItem.pub_date || detailItem.created_at) }}</span>
        </div>
        <h2 class="detail-title">{{ detailItem.title || "(无标题)" }}</h2>
        <div class="detail-content">{{ detailItem.content_summary || detailItem.summary || "暂无摘要" }}</div>
      </template>
      <template #footer>
        <el-button type="primary" :icon="Link" @click="openDetailLink">打开原文</el-button>
        <el-button :type="isDetailFavorited ? 'warning' : 'default'" :icon="isDetailFavorited ? StarFilled : Star" @click="toggleDetailFavorite">
          {{ isDetailFavorited ? "已收藏" : "收藏此新闻" }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="dialogVisible"
      title="Grok 决策提示词"
      width="700px"
      class="grok-dialog"
      destroy-on-close
    >
      <el-input v-model="grokPrompt" type="textarea" :rows="15" readonly class="grok-textarea" />
      <template #footer>
        <el-button @click="copyPrompt">复制到剪贴板</el-button>
        <el-button type="primary" @click="saveAsDecision">保存为决策日志</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import debounce from "lodash-es/debounce";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Refresh, Delete, Document, Link, Star, StarFilled, ArrowDown, Loading } from "@element-plus/icons-vue";
import * as XLSX from "xlsx";
import html2pdf from "html2pdf.js";
import { getNewsList, postNewsGrokDecision, batchGrok } from "../api/news";
import { getWatchedFunds } from "../api/config";

const REFRESH_INTERVAL = 60000;
const PAGE_SIZE = 50;

const newsList = ref([]);
const newsTotal = ref(0);
const currentPage = ref(1);
const loadingMore = ref(false);
const searchKeyword = ref("");
const sortBy = ref("pub_date desc");
const selectedFund = ref("全部");
const fundOptions = ref(["110011", "510300", "000001", "161725"]);
const loading = ref(false);
const grokLoading = ref(false);
const dialogVisible = ref(false);
const grokPrompt = ref("");
const detailDialogVisible = ref(false);
const detailItem = ref(null);
const favRefresh = ref(0);
const activeTab = ref("all");
const selectedLinks = ref([]);
const searchInputRef = ref(null);
const pageRef = ref(null);
const sentinelRef = ref(null);
const touchStartY = ref(0);
const router = useRouter();

function onTouchStart(e) {
  const scrollTop = window.scrollY ?? document.documentElement.scrollTop ?? 0;
  if (scrollTop < 10) touchStartY.value = e.touches[0].clientY;
}

function onTouchEnd(e) {
  if (touchStartY.value > 0) {
    const dy = e.changedTouches[0].clientY - touchStartY.value;
    if (dy > 60) loadNews();
  }
  touchStartY.value = 0;
}

const displayCount = computed(() => displayList.value?.length ?? 0);

const showInfiniteScroll = computed(() =>
  activeTab.value === "all" && newsTotal.value > PAGE_SIZE && newsList.value.length < newsTotal.value
);

const displayList = computed(() => {
  favRefresh.value; // react to favorites change
  if (activeTab.value === "favorites") return getFavorites();
  return newsList.value;
});

function isSelected(link) {
  return selectedLinks.value.includes(link);
}

function toggleSelect(link, checked) {
  if (!link) return;
  const idx = selectedLinks.value.indexOf(link);
  if (checked && idx < 0) selectedLinks.value = [...selectedLinks.value, link];
  else if (!checked && idx >= 0)
    selectedLinks.value = selectedLinks.value.filter((l) => l !== link);
}

function clearSelection() {
  selectedLinks.value = [];
}

const batchGenerateGrok = async () => {
  if (selectedLinks.value.length === 0) return;
  grokLoading.value = true;
  try {
    const res = await batchGrok(selectedLinks.value);
    const data = res?.data ?? res;
    grokPrompt.value = data?.prompt ?? "";
    dialogVisible.value = true;
  } catch {
    ElMessage.error("批量生成失败");
  } finally {
    grokLoading.value = false;
  }
};

const NEWS_FAVORITES_KEY = "news_favorites";

function getFavorites() {
  try {
    const raw = localStorage.getItem(NEWS_FAVORITES_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function isFavorited(link) {
  if (!link) return false;
  const list = getFavorites();
  return list.some((f) => f.link === link);
}

function saveFavorites(list) {
  localStorage.setItem(NEWS_FAVORITES_KEY, JSON.stringify(list));
}

const isDetailFavorited = computed(() => {
  favRefresh.value; // dependency for reactivity when toggling
  return detailItem.value ? isFavorited(detailItem.value.link) : false;
});

function openDetail(item) {
  detailItem.value = item;
  detailDialogVisible.value = true;
}

function openDetailLink() {
  try {
    if (detailItem.value?.link) window.open(detailItem.value.link, "_blank");
  } catch {
    ElMessage.error("打开链接失败");
  }
}

function toggleDetailFavorite() {
  if (!detailItem.value) return;
  try {
  const list = getFavorites();
  const link = detailItem.value.link;
  const idx = list.findIndex((f) => f.link === link);
  if (idx >= 0) {
    list.splice(idx, 1);
    ElMessage.success("已取消收藏");
  } else {
    list.push({
      link: detailItem.value.link,
      title: detailItem.value.title,
      source: detailItem.value.source,
      pub_date: detailItem.value.pub_date,
    });
    ElMessage.success("已收藏");
  }
  saveFavorites(list);
  favRefresh.value++;
  } catch {
    ElMessage.error("操作失败");
  }
}

function sentimentType(item) {
  const s = item.sentiment_score ?? item.sentiment ?? 0;
  if (s > 0.3) return "success";
  if (s < -0.3) return "danger";
  return "info";
}

function sentimentLabel(item) {
  const s = item.sentiment_score ?? item.sentiment ?? 0;
  if (s > 0.3) return "利好";
  if (s < -0.3) return "利空";
  return "中性";
}

function sortToParam(s: string): string | undefined {
  if (!s || s === "pub_date desc") return "pub_date,-1";
  if (s === "pub_date asc") return "pub_date,1";
  if (s === "sentiment desc") return "sentiment,-1";
  if (s === "sentiment asc") return "sentiment,1";
  return "pub_date,-1";
}

function formatDate(val) {
  if (!val) return "-";
  const s = typeof val === "string" ? val : val?.toISOString?.() ?? String(val);
  return s.slice(0, 19).replace("T", " ");
}

const loadNews = async (opts?: { skipLoading?: boolean; append?: boolean }) => {
  if (!opts?.append && !opts?.skipLoading) loading.value = true;
  if (opts?.append) loadingMore.value = true;
  try {
    const page = opts?.append ? currentPage.value + 1 : 1;
    const fundCode =
      selectedFund.value === "全部" || !selectedFund.value ? undefined : selectedFund.value;
    const res = await getNewsList(
      {
        days: 7,
        fund_code: fundCode ?? undefined,
        keyword: searchKeyword.value.trim() || undefined,
        sort: sortToParam(sortBy.value),
        page,
        limit: PAGE_SIZE,
        refresh: false,
      },
      { skipLoading: opts?.skipLoading ?? opts?.append }
    );
    const data = res?.data ?? res;
    const items = Array.isArray(data?.items) ? data.items : [];
    if (opts?.append) {
      newsList.value = [...newsList.value, ...items];
      currentPage.value = page;
    } else {
      newsList.value = items;
      currentPage.value = 1;
    }
    newsTotal.value = data?.total ?? items.length;
  } catch {
    newsList.value = opts?.append ? newsList.value : [];
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
};

const loadMoreNews = () => {
  if (loadingMore.value || !showInfiniteScroll.value) return;
  loadNews({ append: true, skipLoading: true });
};

const generateGrokDecision = async () => {
  grokLoading.value = true;
  try {
    const fc =
      selectedFund.value === "全部" || !selectedFund.value ? "" : selectedFund.value;
    const res = await postNewsGrokDecision({ fund_code: fc, include_news: true });
    const data = res?.data ?? res;
    grokPrompt.value = data?.prompt ?? "";
    dialogVisible.value = true;
  } catch {
    ElMessage.error("生成失败");
  } finally {
    grokLoading.value = false;
  }
};

function exportNewsToExcel() {
  try {
    const list = displayList.value;
    if (!list || list.length === 0) {
      ElMessage.warning("暂无数据可导出");
      return;
    }
    const rows = [
    ["标题", "来源", "发布时间", "摘要", "链接", "情绪"],
    ...list.map((item) => [
      item.title ?? "",
      item.source ?? "",
      formatDate(item.pub_date || item.created_at),
      (item.content_summary || item.summary || "").slice(0, 500),
      item.link ?? "",
      sentimentLabel(item),
    ]),
  ];
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet(rows);
  XLSX.utils.book_append_sheet(wb, ws, "市场资讯");
  const fn = `市场资讯-${new Date().toISOString().slice(0, 10)}.xlsx`;
  XLSX.writeFile(wb, fn);
  ElMessage.success("导出成功");
  } catch {
    ElMessage.error("导出失败");
  }
}

async function exportNewsToPdf() {
  const list = displayList.value;
  if (!list || list.length === 0) {
    ElMessage.warning("暂无数据可导出");
    return;
  }
  const rows = list
    .map(
      (item) => `
    <tr>
      <td style="border:1px solid #dcdfe6;padding:6px 8px;font-size:11px;">${(item.title ?? "").replace(/</g, "&lt;").slice(0, 80)}</td>
      <td style="border:1px solid #dcdfe6;padding:6px 8px;font-size:11px;">${(item.source ?? "").replace(/</g, "&lt;")}</td>
      <td style="border:1px solid #dcdfe6;padding:6px 8px;font-size:11px;">${formatDate(item.pub_date || item.created_at)}</td>
      <td style="border:1px solid #dcdfe6;padding:6px 8px;font-size:10px;">${((item.content_summary || item.summary || "").slice(0, 200) + "…").replace(/</g, "&lt;")}</td>
    </tr>`
    )
    .join("");
  const htmlContent = `
<div style="font-family:'Microsoft YaHei',sans-serif;font-size:12px;padding:16px;">
  <h1 style="font-size:16px;margin-bottom:12px;">市场资讯 - 导出</h1>
  <p style="font-size:11px;color:#909399;">导出时间：${new Date().toLocaleString("zh-CN")}，共 ${list.length} 条</p>
  <table style="width:100%;border-collapse:collapse;margin-top:12px;">
    <thead><tr>
      <th style="border:1px solid #dcdfe6;padding:6px 8px;background:#f5f7fa;font-size:11px;">标题</th>
      <th style="border:1px solid #dcdfe6;padding:6px 8px;background:#f5f7fa;font-size:11px;">来源</th>
      <th style="border:1px solid #dcdfe6;padding:6px 8px;background:#f5f7fa;font-size:11px;">时间</th>
      <th style="border:1px solid #dcdfe6;padding:6px 8px;background:#f5f7fa;font-size:11px;">摘要</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>
</div>`;
  const el = document.createElement("div");
  el.innerHTML = htmlContent;
  el.style.position = "absolute";
  el.style.left = "-9999px";
  el.style.width = "210mm";
  document.body.appendChild(el);
  try {
    await html2pdf().set({
      margin: 10,
      filename: `市场资讯-${new Date().toISOString().slice(0, 10)}.pdf`,
      image: { type: "jpeg", quality: 0.98 },
      html2canvas: { scale: 2 },
      jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
    }).from(el).save();
    ElMessage.success("导出成功");
  } catch {
    ElMessage.error("导出失败");
  } finally {
    document.body.removeChild(el);
  }
}

function handleExport(command) {
  if (command === "excel") exportNewsToExcel();
  else if (command === "pdf") exportNewsToPdf();
}

const copyPrompt = () => {
  try {
    if (!grokPrompt.value) {
      ElMessage.warning("暂无内容可复制");
      return;
    }
    navigator.clipboard.writeText(grokPrompt.value).then(
      () => ElMessage.success("已复制到剪贴板，可直接发给 Grok"),
      () => ElMessage.error("复制失败")
    );
  } catch {
    ElMessage.error("复制失败");
  }
};

const debouncedLoadNews = debounce(() => loadNews(), 300);

const clearFilters = () => {
  searchKeyword.value = "";
  sortBy.value = "pub_date desc";
  loadNews();
};

const saveAsDecision = () => {
  try {
    if (!grokPrompt.value) return;
    const fc =
      selectedFund.value === "全部" || !selectedFund.value ? "" : selectedFund.value;
    sessionStorage.setItem(
      "grokPromptFromNews",
      JSON.stringify({ grok_prompt: grokPrompt.value, fund_code: fc })
    );
    dialogVisible.value = false;
    router.push({ name: "DecisionLog" });
    ElMessage.success("已跳转到决策日志，请填写并提交");
  } catch {
    ElMessage.error("保存失败");
  }
};

let refreshTimer = null;
let observer = null;

function onKeydown(e) {
  const mod = e.ctrlKey || e.metaKey;
  if (!mod) return;
  if (e.key === "r") {
    e.preventDefault();
    loadNews();
  } else if (e.key === "k") {
    e.preventDefault();
    searchInputRef.value?.focus?.();
  } else if (e.key === "g") {
    e.preventDefault();
    generateGrokDecision();
  }
}

onMounted(async () => {
  try {
    const res = await getWatchedFunds();
    const codes = res?.data?.fund_codes ?? [];
    if (codes.length > 0) {
      fundOptions.value = [...new Set([...fundOptions.value, ...codes])];
    }
  } catch {
    /* ignore */
  }
  loadNews();
  refreshTimer = setInterval(() => loadNews({ skipLoading: true }), REFRESH_INTERVAL);
  window.addEventListener("keydown", onKeydown);

  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) loadMoreNews();
    },
    { rootMargin: "100px", threshold: 0 }
  );
  watch(sentinelRef, (el, prev) => {
    try {
      if (prev && prev instanceof Element) observer?.unobserve(prev);
      if (el && el instanceof Element) observer?.observe(el);
    } catch {}
  }, { immediate: true });
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
  debouncedLoadNews.cancel();
  window.removeEventListener("keydown", onKeydown);
  observer?.disconnect?.();
});
</script>

<style scoped>
.news-page {
  padding: 20px;
  padding-bottom: calc(20px + env(safe-area-inset-bottom, 0px));
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  margin: 0 0 8px;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.page-desc {
  margin: 0;
  font-size: 0.9rem;
  color: var(--el-text-color-secondary);
}

.tabs-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.count-badge {
  margin-left: auto;
}

@media (max-width: 768px) {
  .page-title { font-size: 1.25rem; }
  .page-desc { font-size: 0.8rem; }
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  margin-bottom: 16px;
}

.toolbar-sticky {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--el-bg-color);
  padding: 12px 16px;
  margin: 0 -20px 16px -20px;
  padding-left: 20px;
  padding-right: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

html.dark .toolbar-sticky {
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
}

.toolbar-hint {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

@media (max-width: 768px) {
  .toolbar-hint { display: none; }
}

.news-tabs {
  margin-bottom: 16px;
}

.news-tabs :deep(.el-tabs__content) {
  display: none;
}

.news-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.selection-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 16px;
  background: var(--el-color-primary-light-9);
  border-radius: 8px;
}

html.dark .selection-bar {
  background: var(--el-color-primary-dark-2);
}

.selection-count {
  font-size: 14px;
  color: var(--el-text-color-primary);
  font-weight: 500;
}

.filter-card {
  margin-bottom: 24px;
  background: var(--el-bg-color);
}

.filter-card :deep(.el-card__body) {
  padding: 16px 20px;
}

.filter-row {
  align-items: center;
}

.search-input {
  width: 100%;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 8px;
}

.filter-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

@media (max-width: 768px) {
  .filter-actions {
    margin-top: 12px;
  }
}

.news-grid {
  margin-top: 0;
  min-height: 120px;
}

.news-card {
  margin-bottom: 20px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
  height: 100%;
}

.news-card-clickable {
  cursor: pointer;
}

.news-card:hover {
  transform: scale(1.02);
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.06);
}

.news-card-selected {
  border-color: var(--el-color-primary) !important;
  box-shadow: 0 0 0 2px var(--el-color-primary-light-5);
}

html.dark .news-card-selected {
  box-shadow: 0 0 0 2px var(--el-color-primary-dark-2);
}

html.dark .news-card:hover {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.35);
}

.news-card :deep(.el-card__header) {
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.news-card :deep(.el-card__body) {
  padding: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.card-source {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.card-date {
  margin-left: auto;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.news-title {
  display: block;
  font-size: 1rem;
  font-weight: 600;
  color: var(--el-color-primary);
  text-decoration: none;
  margin: 0 0 10px;
  line-height: 1.5;
}

.news-title:hover {
  color: var(--el-color-primary-light-3);
  text-decoration: underline;
}

.summary {
  color: var(--el-text-color-secondary);
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 768px) {
  .news-title { font-size: 0.9rem; }
  .summary { font-size: 12px; }
  .card-source, .card-date { font-size: 11px; }
}

.infinite-sentinel {
  height: 1px;
  width: 100%;
  visibility: hidden;
  pointer-events: none;
}

.load-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.empty-state {
  padding: 48px 0;
}

.empty-state :deep(.el-empty__description) {
  margin-top: 12px;
}

.skeleton-card :deep(.el-card__header) {
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.skeleton-card :deep(.el-card__body) {
  padding: 16px;
}

.skeleton-grid .card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.news-fade-enter-active,
.news-fade-leave-active {
  transition: opacity 0.25s ease;
}

.news-fade-enter-from,
.news-fade-leave-to {
  opacity: 0;
}

/* 新闻详情弹窗 */
.news-detail-dialog :deep(.el-dialog__body) {
  padding: 0 20px 20px;
  color: var(--el-text-color-primary);
}

.detail-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.detail-source {
  font-weight: 500;
}

.detail-date {
  margin-left: auto;
  color: var(--el-text-color-placeholder);
}

.detail-title {
  margin: 0 0 16px;
  font-size: 1.25rem;
  font-weight: 600;
  line-height: 1.5;
  color: var(--el-text-color-primary);
}

.detail-content {
  font-size: 15px;
  line-height: 1.75;
  color: var(--el-text-color-regular);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 320px;
  overflow-y: auto;
}

html.dark .news-detail-dialog :deep(.el-dialog) {
  background: var(--el-bg-color);
}

.grok-dialog :deep(.el-dialog__body) {
  padding-top: 12px;
}

.grok-textarea {
  font-family: var(--el-font-family-mono, "Consolas", "Monaco", monospace);
  font-size: 13px;
  line-height: 1.5;
}

.grok-textarea :deep(.el-textarea__inner) {
  border-radius: 8px;
}
</style>
