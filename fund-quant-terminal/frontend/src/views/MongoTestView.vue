<!--
  =====================================================
  MongoDB 连接状态测试
  =====================================================
-->
<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElCard, ElButton, ElDescriptions, ElDescriptionsItem, ElTag } from "element-plus";
import { request } from "../api/request";

const loading = ref(false);
const status = ref<{
  connected?: boolean;
  database?: string;
  ping?: boolean;
  message?: string;
  error?: string;
} | null>(null);

async function testConnection() {
  loading.value = true;
  status.value = null;
  try {
    const res = (await request.get("/mongo/status")) as unknown as {
      data?: { connected?: boolean; database?: string; ping?: boolean; message?: string };
      message?: string;
    };
    status.value = {
      ...res?.data,
      connected: res?.data?.connected ?? false,
    };
  } catch (e: unknown) {
    const msg =
      (e as { response?: { data?: { message?: string } } })?.response?.data?.message ??
      (e instanceof Error ? e.message : "连接失败");
    status.value = { connected: false, error: msg };
  } finally {
    loading.value = false;
  }
}

onMounted(testConnection);
</script>

<template>
  <div class="mongo-test">
    <h2 class="page-title">MongoDB 连接测试</h2>
    <ElCard shadow="never">
      <ElButton type="primary" :loading="loading" @click="testConnection">
        检测连接
      </ElButton>
      <ElDescriptions v-if="status" class="status-desc" :column="1" border>
        <ElDescriptionsItem label="连接状态">
          <ElTag :type="status.connected ? 'success' : 'danger'">
            {{ status.connected ? "已连接" : "未连接" }}
          </ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="数据库">
          {{ status.database ?? "-" }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="Ping">
          {{ status.ping ? "正常" : status.connected ? "正常" : "-" }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="说明">
          {{ status.message ?? status.error ?? "-" }}
        </ElDescriptionsItem>
      </ElDescriptions>
    </ElCard>
  </div>
</template>

<style scoped>
.mongo-test {
  max-width: 600px;
}

.page-title {
  margin: 0 0 20px;
}

.status-desc {
  margin-top: 20px;
}
</style>
