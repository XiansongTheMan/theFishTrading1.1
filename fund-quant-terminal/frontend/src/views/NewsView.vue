<!--
  =====================================================
  新闻资讯 - 展示全部与新闻相关的内容
  =====================================================
-->
<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import {
  ElCard,
  ElButton,
  ElSelect,
  ElOption,
  ElCheckbox,
  ElMessage,
  ElEmpty,
  ElTag,
} from "element-plus";
import { RefreshRight } from "@element-plus/icons-vue";
import { fetchNews } from "../api/news";
import type { NewsItem } from "../api/news";
import { getWatchedFunds } from "../api/config";

const router = useRouter();
const loading = ref(false);
const newsList = ref<NewsItem[]>([]);
const fundCode = ref("");
const days = ref(7);
const useRefresh = ref(true);
const watchedFunds = ref<string[]>([]);

onMounted(async () => {
  try {
    const res = await getWatchedFunds();
    watchedFunds.value = res?.data?.fund_codes ?? [];
    if (watchedFunds.value.length > 0 && !fundCode.value) {
      fundCode.value = "";
    }
  } catch {
    watchedFunds.value = [];
  }
  await loadNews();
});

async function loadNews() {
  if (loading.value) return;
  loading.value = true;
  try {
    const res = (await fetchNews({
      fund_code: fundCode.value.trim() || undefined,
      days: days.value,
      refresh: useRefresh.value,
    })) as { data?: NewsItem[]; code?: number };
    const data = res?.data;
    newsList.value = Array.isArray(data) ? data : [];
    if (newsList.value.length > 0) {
      ElMessage.success(`共加载 ${newsList.value.length} 条新闻`);
    } else {
      ElMessage.warning(
        "未获取到新闻。RSS 源可能受限，可取消勾选「从 RSS 重新抓取」仅读缓存，或稍后重试"
      );
    }
  } catch (e) {
    console.error(e);
    ElMessage.error("加载新闻失败");
    newsList.value = [];
  } finally {
    loading.value = false;
  }
}

function goToGrokDecision() {
  router.push("/decisions");
}
</script>

<template>
  <div class="news-view">
    <h2 class="page-title">新闻资讯</h2>

    <ElCard shadow="never" class="filter-card">
      <div class="filter-row">
        <ElSelect
          v-model="fundCode"
          placeholder="全部基金 / 输入或选择"
          filterable
          allow-create
          clearable
          style="width: 180px"
        >
          <ElOption label="(全部)" value="" />
          <ElOption
            v-for="code in watchedFunds"
            :key="code"
            :label="code"
            :value="code"
          />
        </ElSelect>
        <ElSelect v-model="days" style="width: 120px">
          <ElOption :value="3" label="最近 3 天" />
          <ElOption :value="7" label="最近 7 天" />
          <ElOption :value="14" label="最近 14 天" />
          <ElOption :value="30" label="最近 30 天" />
        </ElSelect>
        <ElCheckbox v-model="useRefresh">从 RSS 重新抓取</ElCheckbox>
        <ElButton type="primary" :icon="RefreshRight" :loading="loading" @click="loadNews">
          刷新
        </ElButton>
        <ElButton plain @click="goToGrokDecision">
          生成 Grok 决策
        </ElButton>
      </div>
    </ElCard>

    <ElCard v-if="newsList.length > 0" class="news-card" shadow="never">
      <template #header>
        <span>新闻列表</span>
        <ElTag size="small" type="info">{{ newsList.length }} 条</ElTag>
      </template>
      <div class="news-list">
        <div v-for="(item, i) in newsList" :key="i" class="news-item">
          <a
            v-if="item.link"
            :href="item.link"
            target="_blank"
            rel="noopener"
            class="news-title"
          >{{ item.title || "(无标题)" }}</a>
          <span v-else class="news-title">{{ item.title || "(无标题)" }}</span>
          <p v-if="item.content_summary" class="news-summary">{{ item.content_summary }}</p>
          <div class="news-meta">
            <ElTag v-if="item.fund_code" size="small" type="primary">{{ item.fund_code }}</ElTag>
            <span>{{ item.pub_date || item.created_at || "-" }}</span>
            <span>{{ item.source || "RSS" }}</span>
          </div>
        </div>
      </div>
    </ElCard>

    <ElCard v-else-if="!loading" class="empty-card" shadow="never">
      <ElEmpty>
        <template #description>
          <p>暂无新闻数据</p>
          <p class="empty-hint">可取消勾选「从 RSS 重新抓取」后点刷新，仅从缓存读取；RSS 源若不可达需检查网络</p>
        </template>
      </ElEmpty>
    </ElCard>
  </div>
</template>

<style scoped>
.news-view {
  max-width: 1000px;
}

.page-title {
  margin: 0 0 20px;
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

.news-card {
  margin-top: 0;
}

.news-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 70vh;
  overflow-y: auto;
}

.news-item {
  padding: 14px 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-fill-color-blank);
  transition: border-color 0.2s;
}

.news-item:hover {
  border-color: var(--el-color-primary-light-5);
}

.news-title {
  font-weight: 500;
  font-size: 15px;
  color: var(--el-color-primary);
  text-decoration: none;
  display: block;
  margin-bottom: 6px;
}

.news-title:hover {
  text-decoration: underline;
}

.news-summary {
  margin: 0 0 8px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
  font-size: 13px;
}

.news-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.empty-card {
  margin-top: 20px;
}

.empty-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
