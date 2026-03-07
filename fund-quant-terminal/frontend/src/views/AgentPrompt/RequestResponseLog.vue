<script setup lang="ts">
import { ElCard, ElCollapse, ElCollapseItem } from "element-plus";

interface RequestData {
  agent: string;
  content: string;
  messages?: Array<{ role: string; content: string }>;
}

interface ResponseData {
  ok: boolean;
  content: string;
}

defineProps<{
  request?: RequestData | null;
  response?: ResponseData | null;
}>();
</script>

<template>
  <ElCard shadow="never" class="log-card">
    <ElCollapse>
      <ElCollapseItem title="请求 (Request)" name="request">
        <pre v-if="request" class="json-block">{{ JSON.stringify(request, null, 2) }}</pre>
        <span v-else class="empty-hint">暂无数据</span>
      </ElCollapseItem>
      <ElCollapseItem title="响应 (Response)" name="response">
        <pre v-if="response" class="json-block">{{ JSON.stringify(response, null, 2) }}</pre>
        <span v-else class="empty-hint">暂无数据</span>
      </ElCollapseItem>
    </ElCollapse>
  </ElCard>
</template>

<style scoped>
.log-card { margin-top: 12px; }
.json-block { margin: 0; font-size: 0.85rem; white-space: pre-wrap; word-break: break-all; }
.empty-hint { color: var(--el-text-color-placeholder); font-size: 0.9rem; }
</style>
