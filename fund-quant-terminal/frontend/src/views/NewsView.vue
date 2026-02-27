<!--
  市场资讯 - 东方财富 + 新浪基金实时新闻
-->
<template>
  <div class="news-page">
    <el-page-header title="市场资讯" content="东方财富 + 新浪基金实时新闻" />
    <el-row :gutter="20" class="filter-row">
      <el-col :xs="24" :sm="18">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索标题或关键词"
          clearable
          @keyup.enter="loadNews"
        />
      </el-col>
      <el-col :xs="24" :sm="6">
        <el-button type="primary" :loading="grokLoading" @click="generateGrokDecision">
          一键生成 Grok 决策
        </el-button>
      </el-col>
    </el-row>

    <el-row :gutter="20" v-loading="loading" class="news-grid">
      <el-col v-for="(item, idx) in newsList" :key="item.link || idx" :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="news-card">
          <template #header>
            <el-tag :type="sentimentType(item)">
              {{ sentimentLabel(item) }}
            </el-tag>
            <span class="card-source">{{ item.source || "RSS" }}</span>
          </template>
          <a :href="item.link" target="_blank" rel="noopener" class="news-title">
            {{ item.title || "(无标题)" }}
          </a>
          <p class="summary">{{ item.content_summary || item.summary || "" }}</p>
          <div class="footer">{{ formatDate(item.pub_date || item.created_at) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!loading && newsList.length === 0" description="暂无新闻数据" />

    <el-dialog v-model="dialogVisible" title="Grok 决策提示词" width="700px" destroy-on-close>
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
}

.filter-row {
  margin-bottom: 20px;
}

.news-grid {
  margin-top: 16px;
}

.news-card {
  margin-bottom: 16px;
  background: var(--el-bg-color);
}

.news-card .card-source {
  margin-left: 10px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.news-title {
  display: block;
  font-size: 16px;
  font-weight: bold;
  color: var(--el-color-primary);
  text-decoration: none;
  margin-bottom: 8px;
}

.news-title:hover {
  text-decoration: underline;
}

.summary {
  color: var(--el-text-color-secondary);
  margin: 12px 0;
  font-size: 13px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.footer {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.grok-textarea {
  font-family: var(--el-font-family-mono, monospace);
  font-size: 13px;
}
</style>
