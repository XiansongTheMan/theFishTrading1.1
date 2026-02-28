<!--
  =====================================================
  接口 - 展示除 akshare、tushare 外的外部接口及功能
  =====================================================
-->
<script setup lang="ts">
import { ElCard, ElTable, ElTableColumn, ElTag, ElDescriptions, ElDescriptionsItem } from "element-plus";

/** 外部接口定义（排除 akshare、tushare） */
const interfaces = [
  {
    name: "RSSHub - 东方财富滚动",
    url: "https://rsshub.app/finance/eastmoney/roll",
    method: "GET",
    type: "RSS",
    desc: "东方财富网滚动财经新闻，用于新闻抓取与 Grok 决策提示词生成",
  },
  {
    name: "RSSHub - 东方财富基金",
    url: "https://rsshub.app/finance/eastmoney/fund/{fund_code}",
    method: "GET",
    type: "RSS",
    desc: "指定基金相关新闻，{fund_code} 替换为基金代码，用于基金维度的新闻筛选",
  },
  {
    name: "RSSHub - 新浪财经滚动",
    url: "https://rsshub.app/finance/sina/roll",
    method: "GET",
    type: "RSS",
    desc: "新浪财经滚动新闻，用于新闻抓取与 Grok 决策提示词生成",
  },
  {
    name: "MongoDB",
    url: "mongodb://localhost:27017",
    method: "-",
    type: "数据库",
    desc: "本地数据库，存储决策日志、资产、持仓、新闻缓存、配置、Agent 角色设定等",
  },
];
</script>

<template>
  <div class="interfaces-view">
    <h2 class="page-title">接口</h2>
    <p class="page-desc">除 akshare、tushare 外的外部接口及功能说明</p>

    <ElCard shadow="never">
      <ElTable :data="interfaces" stripe>
        <ElTableColumn label="接口名称" min-width="160">
          <template #default="{ row }">
            <span class="interface-name">{{ row.name }}</span>
          </template>
        </ElTableColumn>
        <ElTableColumn label="类型" width="90">
          <template #default="{ row }">
            <ElTag :type="row.type === 'RSS' ? 'success' : 'info'" size="small">
              {{ row.type }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="URL / 地址" min-width="320">
          <template #default="{ row }">
            <code class="url-text">{{ row.url }}</code>
          </template>
        </ElTableColumn>
        <ElTableColumn label="请求方式" width="90" align="center">
          <template #default="{ row }">{{ row.method }}</template>
        </ElTableColumn>
        <ElTableColumn label="功能说明" min-width="280">
          <template #default="{ row }">
            <span class="desc-text">{{ row.desc }}</span>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>

    <ElCard shadow="never" class="usage-card">
      <template #header>使用场景</template>
      <ElDescriptions :column="1" border>
        <ElDescriptionsItem label="RSS 新闻源">
          新闻页面、定时新闻采集（APScheduler 每 4 小时）、Grok 决策提示词中的资讯摘要均依赖上述 RSS 接口
        </ElDescriptionsItem>
        <ElDescriptionsItem label="MongoDB">
          所有持久化数据存储于 fund_quant 数据库，包括 decision_logs、assets、news_raw、config、grok_prompts 等集合
        </ElDescriptionsItem>
      </ElDescriptions>
    </ElCard>
  </div>
</template>

<style scoped>
.interfaces-view {
  max-width: 1100px;
}

.page-title {
  margin: 0 0 8px;
}

.page-desc {
  margin: 0 0 20px;
  color: var(--el-text-color-secondary);
  font-size: 0.9rem;
}

.interface-name {
  font-weight: 500;
}

.url-text {
  font-size: 12px;
  background: var(--el-fill-color-light);
  padding: 2px 6px;
  border-radius: 4px;
  word-break: break-all;
}

.desc-text {
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.usage-card {
  margin-top: 20px;
}
</style>
