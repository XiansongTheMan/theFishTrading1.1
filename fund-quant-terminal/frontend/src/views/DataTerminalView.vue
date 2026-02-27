<!--
  =====================================================
  数据终端 - 输入基金代码，拉取并展示表格+图表
  =====================================================
-->
<script setup lang="ts">
import { ref, watch } from "vue";
import { ElCard, ElInput, ElButton, ElTable, ElTableColumn, ElMessage } from "element-plus";
import * as echarts from "echarts";
import { fetchData } from "../api/data";
import { useChartResize } from "../composables/useChartResize";

const fundCode = ref("");
const loading = ref(false);
const tableData = ref<Record<string, unknown>[]>([]);
const chartRef = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;

useChartResize(chartRef, () => chartInstance);

async function handleFetch() {
  const code = fundCode.value.trim();
  if (!code) return;
  if (loading.value) return;
  loading.value = true;
  try {
    const res = await fetchData(code, "nav") as { data?: { data?: Record<string, unknown>[] } };
    const inner = res?.data;
    const arr = (inner && typeof inner === "object" && "data" in inner)
      ? (inner.data as Record<string, unknown>[]) ?? []
      : [];
    tableData.value = arr;
    ElMessage.success("数据已刷新");

    if (chartRef.value) {
      if (!chartInstance) chartInstance = echarts.init(chartRef.value);
      const dates = arr.map((r: Record<string, unknown>) => String(r.date ?? r["净值日期"] ?? "")).filter(Boolean);
      const values = arr.map((r: Record<string, unknown>) => Number(r.nav ?? r["单位净值"] ?? 0));
      chartInstance.setOption({
        tooltip: { trigger: "axis" },
        xAxis: { type: "category", data: dates },
        yAxis: { type: "value", name: "单位净值" },
        series: [{ name: "单位净值", type: "line", data: values, smooth: true }],
      });
    }
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

watch(
  () => chartRef.value,
  (el) => {
    if (el && tableData.value.length) {
      chartInstance = echarts.init(el);
      const dates = tableData.value.map((r: Record<string, unknown>) => String(r.date ?? r["净值日期"] ?? "")).filter(Boolean);
      const values = tableData.value.map((r: Record<string, unknown>) => Number(r.nav ?? r["单位净值"] ?? 0));
      chartInstance.setOption({
        tooltip: { trigger: "axis" },
        xAxis: { type: "category", data: dates },
        yAxis: { type: "value", name: "单位净值" },
        series: [{ name: "单位净值", type: "line", data: values, smooth: true }],
      });
    }
  },
  { immediate: true }
);
</script>

<template>
  <div class="data-terminal">
    <h2 class="page-title">数据终端</h2>
    <ElCard shadow="never">
      <div class="fetch-row">
        <ElInput
          v-model="fundCode"
          placeholder="请输入基金代码，如 000001"
          style="max-width: 260px; margin-right: 12px"
          clearable
          @keyup.enter="handleFetch"
        />
        <ElButton type="primary" :loading="loading" @click="handleFetch">
          拉取净值
        </ElButton>
      </div>
    </ElCard>

    <ElCard v-if="tableData.length > 0" class="table-card" shadow="never">
      <template #header>净值数据</template>
      <div class="table-scroll-x">
      <ElTable :data="tableData" stripe max-height="300">
        <ElTableColumn label="日期" width="120">
          <template #default="{ row }">{{ row.date ?? row["净值日期"] ?? "-" }}</template>
        </ElTableColumn>
        <ElTableColumn label="单位净值" width="120">
          <template #default="{ row }">{{ row.nav ?? row["单位净值"] ?? "-" }}</template>
        </ElTableColumn>
        <ElTableColumn label="日增长率(%)">
          <template #default="{ row }">{{ row.daily_return ?? row["日增长率"] ?? "-" }}</template>
        </ElTableColumn>
      </ElTable>
      </div>
    </ElCard>

    <ElCard v-if="tableData.length > 0" class="chart-card" shadow="never">
      <template #header>净值走势</template>
      <div ref="chartRef" class="chart"></div>
    </ElCard>
  </div>
</template>

<style scoped>
.data-terminal {
  max-width: 1000px;
}

.page-title {
  margin: 0 0 20px;
}

.fetch-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.fetch-row .el-input {
  flex: 1;
  min-width: 120px;
}

.table-card,
.chart-card {
  margin-top: 20px;
}

.chart {
  width: 100%;
  height: 320px;
}

@media (max-width: 480px) {
  .chart {
    height: 240px;
  }
}
</style>
