<!--
  市场资讯 - 东方财富 + 新浪基金实时新闻
-->
<template>
  <div class="news-page">
    <div class="page-header">
      <h1 class="page-title">市场资讯</h1>
      <p class="page-desc">东方财富 + 新浪基金实时新闻</p>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-row :gutter="16" class="filter-row">
        <el-col :xs="24" :sm="17" :md="18">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索标题或关键词，回车查询"
            clearable
            size="default"
            class="search-input"
            @keyup.enter="loadNews"
          />
        </el-col>
        <el-col :xs="24" :sm="7" :md="6">
          <div class="filter-actions">
            <el-button type="primary" :loading="loading" @click="loadNews">查询</el-button>
            <el-button type="success" :loading="grokLoading" @click="generateGrokDecision">
              一键生成 Grok 决策
            </el-button>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-row :gutter="20" v-loading="loading" class="news-grid">
      <el-col v-for="(item, idx) in newsList" :key="item.link || idx" :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="news-card">
          <template #header>
            <div class="card-header">
              <el-tag :type="sentimentType(item)" size="small">
                {{ sentimentLabel(item) }}
              </el-tag>
              <span class="card-source">{{ item.source || "RSS" }}</span>
              <span class="card-date">{{ formatDate(item.pub_date || item.created_at) }}</span>
            </div>
          </template>
          <a :href="item.link" target="_blank" rel="noopener" class="news-title">
            {{ item.title || "(无标题)" }}
          </a>
          <p class="summary">{{ item.content_summary || item.summary || "" }}</p>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!loading && newsList.length === 0" description="暂无新闻数据" class="empty-state">
      <el-button type="primary" @click="loadNews">重新加载</el-button>
    </el-empty>

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
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { getNewsList, postNewsGrokDecision } from "../api/news";

const newsList = ref([]);
const searchKeyword = ref("");
const loading = ref(false);
const grokLoading = ref(false);
const dialogVisible = ref(false);
const grokPrompt = ref("");
const router = useRouter();

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

function formatDate(val) {
  if (!val) return "-";
  const s = typeof val === "string" ? val : val?.toISOString?.() ?? String(val);
  return s.slice(0, 19).replace("T", " ");
}

const loadNews = async () => {
  loading.value = true;
  try {
    const res = await getNewsList({
      days: 7,
      keyword: searchKeyword.value.trim() || undefined,
      page: 1,
      limit: 100,
      refresh: false,
    });
    const data = res?.data ?? res;
    newsList.value = Array.isArray(data?.items) ? data.items : [];
  } catch (e) {
    console.error(e);
    newsList.value = [];
  } finally {
    loading.value = false;
  }
};

const generateGrokDecision = async () => {
  grokLoading.value = true;
  try {
    const res = await postNewsGrokDecision({ fund_code: "", include_news: true });
    const data = res?.data ?? res;
    grokPrompt.value = data?.prompt ?? "";
    dialogVisible.value = true;
  } catch (e) {
    console.error(e);
    ElMessage.error("生成失败");
  } finally {
    grokLoading.value = false;
  }
};

const copyPrompt = () => {
  if (!grokPrompt.value) {
    ElMessage.warning("暂无内容可复制");
    return;
  }
  navigator.clipboard.writeText(grokPrompt.value).then(
    () => ElMessage.success("已复制到剪贴板，可直接发给 Grok"),
    () => ElMessage.error("复制失败")
  );
};

const saveAsDecision = () => {
  if (!grokPrompt.value) return;
  sessionStorage.setItem(
    "grokPromptFromNews",
    JSON.stringify({ grok_prompt: grokPrompt.value, fund_code: "" })
  );
  dialogVisible.value = false;
  router.push({ name: "DecisionLog" });
  ElMessage.success("已跳转到决策日志，请填写并提交");
};

onMounted(() => loadNews());
</script>

<style scoped>
.news-page {
  padding: 20px;
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
  transition: border-color 0.2s, box-shadow 0.2s;
  height: 100%;
}

.news-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

html.dark .news-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
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

.empty-state {
  padding: 48px 0;
}

.empty-state :deep(.el-empty__description) {
  margin-top: 12px;
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
