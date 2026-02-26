<!--
  =====================================================
  资产曲线 - 总资产随时间变化，绿/红盈亏主题
  =====================================================
-->
<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { ElCard } from "element-plus";
import * as echarts from "echarts";
import { useAppStore } from "../stores/app";

const chartRef = ref<HTMLElement | null>(null);
const appStore = useAppStore();
let chartInstance: echarts.ECharts | null = null;

const PROFIT_COLOR = "#67c23a";
const LOSS_COLOR = "#f56c6c";

function renderChart() {
  if (!chartRef.value) return;
  const history = appStore.assetHistory;
  const dates = history.map((p) => p.date);
  const values = history.map((p) => p.value);

  const lineData = values.map((v, i) => {
    const prev = i > 0 ? (values[i - 1] ?? v) : v;
    const isProfit = v >= prev;
    return {
      value: v,
      itemStyle: { color: isProfit ? PROFIT_COLOR : LOSS_COLOR },
    };
  });

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value);
    window.addEventListener("resize", () => chartInstance?.resize());
  }
  chartInstance.setOption({
    tooltip: { trigger: "axis", formatter: "{b}<br/>总资产: {c} 元" },
    xAxis: { type: "category", data: dates, name: "日期" },
    yAxis: { type: "value", name: "总资产（元）" },
    series: [
      {
        name: "总资产",
        type: "line",
        data: lineData,
        smooth: true,
        lineStyle: { width: 2 },
      },
    ],
  });
}

onMounted(() => {
  renderChart();
});

watch(
  () => appStore.assetHistory,
  () => renderChart(),
  { deep: true }
);
</script>

<template>
  <div class="asset-curve">
    <h2 class="page-title">资产曲线</h2>
    <ElCard shadow="never">
      <template #header>
        <span>总资产随时间变化</span>
        <span class="legend">
          <span class="dot profit"></span> 盈利
          <span class="dot loss"></span> 亏损
        </span>
      </template>
      <div ref="chartRef" class="chart" style="height: 360px"></div>
      <p v-if="appStore.assetHistory.length === 1" class="hint">
        暂无历史数据，进行交易或更新持仓后会展示曲线
      </p>
    </ElCard>
  </div>
</template>

<style scoped>
.asset-curve {
  max-width: 900px;
}

.page-title {
  margin: 0 0 20px;
}

.legend {
  float: right;
  font-size: 0.85rem;
  color: var(--el-text-color-secondary);
}

.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}

.dot.profit {
  background: #67c23a;
}

.dot.loss {
  background: #f56c6c;
}

.hint {
  margin-top: 12px;
  color: var(--el-text-color-secondary);
  font-size: 0.9rem;
}
</style>
