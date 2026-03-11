<!--
  news 接口测试 - 华尔街见闻 / 东方财富
  一级 Tab 切换新闻源，根据 sourceVal 渲染对应子组件
-->
<script setup lang="ts">
import { ref, computed } from "vue";
import { ElCard, ElTabs, ElTabPane } from "element-plus";
import { sourceOptions } from "@/news/config";
import WallstreetTest from "./WallstreetTest.vue";
import EastMoneyTest from "./EastMoneyTest.vue";
import CailiansheTest from "./CailiansheTest.vue";

const sourceVal = ref("wallstreetcn");
const safeSourceOptions = computed(() => sourceOptions ?? []);
</script>

<template>
  <div class="news-test">
    <h2 class="page-title">news 接口测试</h2>
    <ElCard shadow="never" class="tab-card">
      <ElTabs v-model="sourceVal" type="border-card" class="tabs-level-1">
        <ElTabPane
          v-for="src in safeSourceOptions"
          :key="src.value"
          :name="src.value"
          :label="src.label"
        >
          <WallstreetTest v-if="sourceVal === 'wallstreetcn'" />
          <EastMoneyTest v-else-if="sourceVal === 'eastmoney'" />
          <CailiansheTest v-else-if="sourceVal === 'cailianshe'" />
        </ElTabPane>
      </ElTabs>
    </ElCard>
  </div>
</template>

<style scoped>
.news-test {
  max-width: 900px;
}

.page-title {
  margin: 0 0 20px;
}

.tab-card :deep(.el-card__body) {
  padding: 0;
}

.tabs-level-1 :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 20px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.tabs-level-1 :deep(.el-tabs__nav-wrap) {
  padding: 0;
}
.tabs-level-1 :deep(.el-tabs__item) {
  font-size: 0.95rem;
  font-weight: 500;
  padding: 0 24px;
  height: 48px;
  line-height: 48px;
}
.tabs-level-1 :deep(.el-tabs__item.is-active) {
  color: var(--el-color-primary);
}
.tabs-level-1 :deep(.el-tabs__content) {
  padding: 20px;
}
.tabs-level-1 :deep(.el-tabs__active-bar) {
  height: 3px;
}
</style>
