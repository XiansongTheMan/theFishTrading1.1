<!--
  =====================================================
  持仓详情 - 业绩走势、买卖标记、投入与收益
  =====================================================
-->
<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElCard, ElButton, ElEmpty, ElRadioGroup, ElRadioButton, ElDialog, ElForm, ElFormItem, ElInputNumber, ElInput, ElDatePicker, ElMessage, ElMessageBox, ElTooltip } from "element-plus";
import * as echarts from "echarts";
import { fetchData, getStockDaily } from "../api/data";
import {
  getHoldingHistory,
  getHoldingTransactions,
  getHoldingSummary,
  createTransaction,
  deleteTransaction,
  clearHoldingTransactions,
  type HoldingTransaction,
  type HoldingSummary,
} from "../api/assets";

const route = useRoute();
const router = useRouter();
const chartRef = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;

const symbol = computed(() => String(route.params.symbol || "").trim());
const assetType = computed(() => String(route.params.assetType || "fund").toLowerCase());
const isFund = computed(() => assetType.value === "fund");

const loading = ref(true);
const error = ref("");
const rawData = ref<{ date: string; value: number }[]>([]);
const dateRange = ref<string>("all");
const summary = ref<HoldingSummary | null>(null);
const transactions = ref<HoldingTransaction[]>([]);

const txDialogVisible = ref(false);
const txForm = ref({ type: "buy" as "buy" | "sell", date: "", price: 0, amount: 0 });
const txSubmitting = ref(false);
const txFormRef = ref<InstanceType<typeof ElForm> | null>(null);

const RANGE_OPTIONS = [
  { value: "1w", label: "近一周" },
  { value: "1m", label: "近一个月" },
  { value: "3m", label: "近三个月" },
  { value: "1y", label: "近一年" },
  { value: "ytd", label: "今年以来" },
  { value: "all", label: "成立来" },
];

function filterByRange(data: { date: string; value: number }[], range: string): { date: string; value: number }[] {
  if (!data.length) return [];
  const sorted = [...data].sort((a, b) => a.date.localeCompare(b.date));
  const lastDate = sorted[sorted.length - 1]?.date ?? "";
  if (!lastDate) return sorted;
  const end = new Date(lastDate);
  let start: Date;
  switch (range) {
    case "1w":
      start = new Date(end);
      start.setDate(start.getDate() - 7);
      break;
    case "1m":
      start = new Date(end);
      start.setMonth(start.getMonth() - 1);
      break;
    case "3m":
      start = new Date(end);
      start.setMonth(start.getMonth() - 3);
      break;
    case "1y":
      start = new Date(end);
      start.setFullYear(start.getFullYear() - 1);
      break;
    case "ytd":
      start = new Date(end.getFullYear(), 0, 1);
      break;
    default:
      return sorted;
  }
  const startStr = `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, "0")}-${String(start.getDate()).padStart(2, "0")}`;
  return sorted.filter((d) => d.date >= startStr);
}

const chartData = computed(() => filterByRange(rawData.value, dateRange.value));

// 找出交易日期在 chartData 中的索引与对应 y 值，用于绘制买卖散点，并携带交易金额用于 tooltip
interface TxPoint {
  date: string;
  pct: number;
  amount: number;
  quantity: number;
  price: number;
}
function getBuySellPoints() {
  const data = chartData.value;
  const trans = transactions.value;
  if (!data.length || !trans.length) return { buyPoints: [] as TxPoint[], sellPoints: [] as TxPoint[] };
  const firstVal = data[0]?.value;
  if (firstVal == null || firstVal === 0) return { buyPoints: [], sellPoints: [] };
  const dateToIdx = new Map<string, number>();
  data.forEach((d, i) => dateToIdx.set(d.date, i));
  const buyPoints: TxPoint[] = [];
  const sellPoints: TxPoint[] = [];
  for (const t of trans) {
    const idx = dateToIdx.get(t.date);
    if (idx == null) continue;
    const val = data[idx]?.value;
    if (val == null) continue;
    const pct = ((val / firstVal) - 1) * 100;
    const amount = t.amount ?? t.quantity * t.price;
    const pt: TxPoint = { date: t.date, pct, amount, quantity: t.quantity, price: t.price };
    if (t.type === "buy") buyPoints.push(pt);
    else sellPoints.push(pt);
  }
  return { buyPoints, sellPoints };
}

async function loadData() {
  const sym = symbol.value;
  if (!sym) {
    error.value = "缺少标的代码";
    summary.value = null;
    transactions.value = [];
    loading.value = false;
    return;
  }
  loading.value = true;
  error.value = "";
  rawData.value = [];
  // 保留 summary/transactions 直到获取新数据，避免刷新时页面闪烁
  try {
    let useCached = false;
    try {
      const cachedRes = (await getHoldingHistory(assetType.value, sym)) as {
        data?: { data?: { date: string; value: number }[] };
      };
      const cached = cachedRes?.data?.data ?? [];
      if (cached.length > 0) {
        rawData.value = cached.map((d) => ({ date: d.date, value: d.value }));
        useCached = true;
      }
    } catch {
      /* 缓存失败则从 API 拉取 */
    }
    if (!useCached) {
      if (isFund.value) {
        const res = (await fetchData(sym, "nav")) as {
          data?: { data?: Record<string, unknown>[] };
        };
        const raw = res?.data?.data ?? [];
        rawData.value = raw.map((r: Record<string, unknown>) => ({
          date: String(r.date ?? r["净值日期"] ?? ""),
          value: Number(r.nav ?? r["单位净值"] ?? 0),
        })).filter((d) => d.date && d.value > 0);
      } else {
        const res = (await getStockDaily(sym)) as {
          data?: { data?: Record<string, unknown>[] };
        };
        const arr = res?.data?.data ?? [];
        rawData.value = arr.map((r: Record<string, unknown>) => ({
          date: String(r["日期"] ?? r.date ?? ""),
          value: Number(r["收盘"] ?? r.close ?? 0),
        })).filter((d) => d.date && d.value > 0);
      }
    }
    const [summaryRes, txRes] = await Promise.all([
      getHoldingSummary(assetType.value, sym),
      getHoldingTransactions(assetType.value, sym),
    ]);
    const newSummary = (summaryRes as { data?: HoldingSummary })?.data ?? null;
    const newTx = (txRes as { data?: HoldingTransaction[] })?.data ?? [];
    summary.value = newSummary;
    transactions.value = newTx;
    if (rawData.value.length === 0) {
      error.value = "暂无历史数据";
    }
  } catch (e) {
    error.value = "加载失败";
    console.error(e);
    summary.value = null;
    transactions.value = [];
  } finally {
    loading.value = false;
  }
}

function openTxDialog(type: "buy" | "sell", date?: string, price?: number) {
  if (!date && chartData.value.length) {
    const last = chartData.value[chartData.value.length - 1];
    date = last?.date ?? "";
    price = last?.value ?? price ?? 0;
  }
  txForm.value = { type, date: date || "", price: price ?? 0, amount: 0 };
  txDialogVisible.value = true;
}

async function submitTx() {
  const { type, date, price, amount } = txForm.value;
  if (!date || !(date + "").trim()) {
    ElMessage.warning("请填写交易日期");
    return;
  }
  if (!amount || amount <= 0 || !price || price <= 0) {
    ElMessage.warning("请填写有效的单价和金额（均需大于 0）");
    return;
  }
  const quantity = amount / price;
  if (quantity <= 0) {
    ElMessage.warning("金额与单价无效，无法计算数量");
    return;
  }
  if (type === "sell" && summary.value) {
    const holdQty = summary.value.quantity ?? 0;
    if (quantity > holdQty) {
      ElMessage.warning(`卖出数量不能超过持仓 ${holdQty.toFixed(2)}`);
      return;
    }
    if (holdQty <= 0) {
      ElMessage.warning("当前无持仓，无法卖出");
      return;
    }
  }
  txSubmitting.value = true;
  try {
    await createTransaction({
      symbol: symbol.value,
      asset_type: assetType.value,
      date,
      type,
      quantity,
      price,
      amount,
    });
    ElMessage.success("交易已记录");
    txDialogVisible.value = false;
    await loadData();
    await nextTick();
    renderChart();
  } catch (e) {
    ElMessage.error((e as Error)?.message || "提交失败");
  } finally {
    txSubmitting.value = false;
  }
}

async function handleDeleteTx(t: HoldingTransaction) {
  const id = t.id;
  if (!id) return;
  try {
    await ElMessageBox.confirm("确定删除该笔交易记录？将同时反向调整持仓。", "删除确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
    await deleteTransaction(assetType.value, symbol.value, id);
    ElMessage.success("已删除");
    await loadData();
    await nextTick();
    renderChart();
  } catch (e) {
    if ((e as { type?: string })?.type !== "cancel") {
      ElMessage.error((e as Error)?.message || "删除失败");
    }
  }
}

async function handleClearAll() {
  try {
    await ElMessageBox.confirm(
      "确定强制清空该基金的全部历史操作？将同时移除对应持仓，此操作不可恢复。",
      "强制清空",
      {
        confirmButtonText: "清空",
        cancelButtonText: "取消",
        type: "warning",
      }
    );
    const res = (await clearHoldingTransactions(assetType.value, symbol.value)) as { data?: { deleted?: number } };
    const count = res?.data?.deleted ?? 0;
    ElMessage.success(`已清空 ${count} 条历史操作`);
    await loadData();
    await nextTick();
    renderChart();
  } catch (e) {
    if ((e as { type?: string })?.type !== "cancel") {
      ElMessage.error((e as Error)?.message || "清空失败");
    }
  }
}

function renderChart() {
  if (!chartRef.value) return;
  const data = chartData.value;
  if (!data.length) return;
  if (!chartInstance) chartInstance = echarts.init(chartRef.value);
  const dates = data.map((d) => d.date);
  const firstVal = data[0]?.value;
  if (firstVal == null || firstVal === 0) return;
  const pctValues = data.map((d) => ((d.value / firstVal) - 1) * 100);
  const minPct = Math.min(0, ...pctValues);
  const maxPct = Math.max(0, ...pctValues);
  const padding = Math.max(1, (maxPct - minPct) * 0.05);
  const { buyPoints, sellPoints } = getBuySellPoints();

  const series: echarts.SeriesOption[] = [
    {
      name: "涨跌幅",
      type: "line",
      data: pctValues,
      smooth: false,
      showSymbol: false,
      z: 1,
    },
  ];
  if (buyPoints.length) {
    series.push({
      name: "买入",
      type: "scatter",
      data: buyPoints.map((d) => ({ value: [d.date, d.pct], amount: d.amount, quantity: d.quantity, price: d.price })),
      symbol: "circle",
      symbolSize: 14,
      symbolKeepAspect: false,
      z: 10,
      itemStyle: { color: "#f56c6c" },
      emphasis: { scale: 1.3 },
    } as echarts.SeriesOption);
  }
  if (sellPoints.length) {
    series.push({
      name: "卖出",
      type: "scatter",
      data: sellPoints.map((d) => ({ value: [d.date, d.pct], amount: d.amount, quantity: d.quantity, price: d.price })),
      symbol: "circle",
      symbolSize: 14,
      symbolKeepAspect: false,
      z: 10,
      itemStyle: { color: "#67c23a" },
      emphasis: { scale: 1.3 },
    } as echarts.SeriesOption);
  }

  chartInstance.setOption({
    title: {
      text: `${isFund.value ? "单位净值" : "收盘价"} 涨跌幅走势`,
      left: "center",
    },
    tooltip: {
      trigger: "axis",
      formatter: (params: unknown) => {
        const pr = params as { name: string; dataIndex: number; value?: number | number[]; seriesName: string; marker: string }[];
        if (!pr?.length) return "";
        const p = pr[0];
        const idx = data.findIndex((d) => d.date === p.name) ?? p.dataIndex ?? 0;
        const rawVal = data[idx]?.value;
        const valLabel = isFund.value ? "净值" : "收盘价";
        let s = p.name + "<br/>";
        if (rawVal != null) s += `${valLabel}: ${Number(rawVal).toFixed(4)}<br/>`;
        pr.forEach((item) => {
          if (item.seriesName === "买入") {
            const tx = buyPoints[item.dataIndex ?? 0];
            if (tx) {
              s += `${item.marker}买入: ¥${Number(tx.amount).toFixed(2)} (${Number(tx.quantity).toFixed(2)} 份 × ¥${Number(tx.price).toFixed(4)})<br/>`;
            } else {
              const val = item.value;
              const v = Array.isArray(val) ? (val[1] as number) : Number(val);
              if (typeof v === "number" && !Number.isNaN(v)) s += `${item.marker}买入: ${v >= 0 ? "+" : ""}${v.toFixed(2)}%<br/>`;
            }
          } else if (item.seriesName === "卖出") {
            const tx = sellPoints[item.dataIndex ?? 0];
            if (tx) {
              s += `${item.marker}卖出: ¥${Number(tx.amount).toFixed(2)} (${Number(tx.quantity).toFixed(2)} 份 × ¥${Number(tx.price).toFixed(4)})<br/>`;
            } else {
              const val = item.value;
              const v = Array.isArray(val) ? (val[1] as number) : Number(val);
              if (typeof v === "number" && !Number.isNaN(v)) s += `${item.marker}卖出: ${v >= 0 ? "+" : ""}${v.toFixed(2)}%<br/>`;
            }
          } else {
            const val = item.value;
            const v = Array.isArray(val) ? (val[1] as number) : Number(val);
            if (typeof v === "number" && !Number.isNaN(v)) {
              s += `${item.marker}${item.seriesName}: ${v >= 0 ? "+" : ""}${v.toFixed(2)}%<br/>`;
            }
          }
        });
        return s;
      },
    },
    xAxis: { type: "category", data: dates },
    yAxis: {
      type: "value",
      name: "涨跌幅（%）",
      axisLabel: { formatter: (v: number) => `${v >= 0 ? "+" : ""}${Number(v).toFixed(2)}%` },
      min: minPct - padding,
      max: maxPct + padding,
      splitLine: { lineStyle: { type: "dashed", opacity: 0.5 } },
    },
    series,
  });

  chartInstance.off("click");
  chartInstance.on("click", (params: { componentType: string; name?: string; seriesName?: string; seriesType?: string; seriesIndex?: number; data?: unknown }) => {
    if (params.componentType !== "series") return;
    const d = params.data as { value?: [string, number] } | undefined;
    const date = (params.name ?? (Array.isArray(params.data) ? params.data[0] : d?.value?.[0])) as string | null;
    if (!date) return;
    const idx = data.findIndex((d) => d.date === date);
    const price = idx >= 0 ? data[idx].value : 0;
    const clickedSell = params.seriesName === "卖出" || (params.seriesType === "scatter" && sellPoints.length > 0 && params.seriesIndex === series.length - 1);
    openTxDialog(clickedSell ? "sell" : "buy", date, price);
  });
}

function goBack() {
  router.push("/assets");
}

async function handleRefreshPage() {
  await loadData();
  await nextTick();
  renderChart();
}

watch([chartRef, chartData, dateRange, transactions], () => {
  if (chartData.value.length > 0) renderChart();
}, { immediate: true });

watch(
  () => [route.params.symbol, route.params.assetType],
  () => loadData(),
  { immediate: true }
);

onMounted(() => {
  window.addEventListener("resize", () => chartInstance?.resize());
});
</script>

<template>
  <div class="holding-detail">
    <div class="header-row">
      <ElButton type="primary" link @click="goBack">← 返回资产</ElButton>
    </div>
    <div class="holding-content" v-loading="loading">
    <!-- 投入资金、持有收益 -->
    <ElCard v-if="summary" shadow="never" class="summary-card">
      <div class="summary-grid">
        <div class="summary-item">
          <span class="label">投入资金</span>
          <span class="value">¥ {{ summary.invested.toFixed(2) }}</span>
        </div>
        <div class="summary-item">
          <span class="label">持有收益</span>
          <span class="value" :class="summary.profit != null && summary.profit >= 0 ? 'profit' : summary.profit != null ? 'loss' : ''">
            <template v-if="summary.profit != null">
              {{ summary.profit >= 0 ? "+" : "" }}{{ summary.profit.toFixed(2) }}
              ({{ summary.profit >= 0 ? "+" : "" }}{{ summary.profit_rate ?? 0 }}%)
            </template>
            <template v-else>未获取</template>
          </span>
        </div>
        <div class="summary-item">
          <span class="label">当前{{ isFund ? "基金" : "股票" }}所属板块</span>
          <span class="value">{{ summary.sector ?? "未获取" }}</span>
        </div>
      </div>
      <div class="action-btns">
        <ElButton type="danger" @click="openTxDialog('buy')">买入</ElButton>
        <ElButton type="success" @click="openTxDialog('sell')">卖出</ElButton>
      </div>
    </ElCard>

    <ElCard shadow="never" class="chart-card">
      <template #header>
        <div class="chart-header">
          <span>{{ symbol }} {{ isFund ? "基金" : "股票" }} - 业绩走势（点击折线节点可买入）</span>
          <ElRadioGroup v-model="dateRange" size="small" class="range-group">
            <ElRadioButton
              v-for="opt in RANGE_OPTIONS"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </ElRadioButton>
          </ElRadioGroup>
        </div>
      </template>
      <div class="chart-body">
        <div class="chart-toolbar">
          <ElButton
            size="small"
            :loading="loading"
            @click="handleRefreshPage"
          >
            刷新
          </ElButton>
        </div>
        <div v-if="error" class="error-tip">
          <ElEmpty :description="error" :image-size="80" />
        </div>
      <div
        v-else-if="chartData.length > 0"
        ref="chartRef"
        class="chart-container"
      />
      <div
        v-else-if="rawData.length > 0 && chartData.length === 0"
        class="empty-tip"
      >
        <ElEmpty description="该时段暂无数据" :image-size="60" />
      </div>
      <div v-else-if="!loading" class="empty-tip">
        <ElEmpty description="暂无数据" :image-size="80" />
      </div>
      </div>
    </ElCard>

    <!-- 历史操作 -->
    <ElCard shadow="never" class="history-card">
      <template #header>
        <div class="history-header">
          <span>历史操作</span>
          <ElTooltip content="清空该基金全部历史操作，并移除对应持仓" placement="top">
            <ElButton
              v-if="transactions.length > 0"
              type="danger"
              plain
              size="small"
              @click="handleClearAll"
            >
              强制清空
            </ElButton>
          </ElTooltip>
        </div>
      </template>
      <div v-if="transactions.length === 0" class="empty-tip">
        <ElEmpty description="暂无交易记录" :image-size="60" />
      </div>
      <div v-else class="history-list">
        <div
          v-for="t in transactions"
          :key="t.id"
          class="history-item"
          :class="t.type === 'buy' ? 'buy' : 'sell'"
        >
          <span class="date">{{ t.date }}</span>
          <span class="type">{{ t.type === "buy" ? "买入" : "卖出" }}</span>
          <span class="qty">{{ t.quantity }}</span>
          <span class="price">¥{{ t.price.toFixed(4) }}</span>
          <span class="amount">¥{{ (t.amount ?? t.quantity * t.price).toFixed(2) }}</span>
          <ElTooltip content="删除该笔交易记录，并反向调整持仓" placement="top">
            <ElButton type="danger" link size="small" @click="handleDeleteTx(t)">删除</ElButton>
          </ElTooltip>
        </div>
      </div>
    </ElCard>
    </div>

    <!-- 买卖弹窗 -->
    <ElDialog
      v-model="txDialogVisible"
      title="交易操作"
      width="360px"
      :close-on-click-modal="false"
    >
      <div class="tx-type-toggle">
        <ElButton :type="txForm.type === 'buy' ? 'primary' : 'default'" @click="txForm.type = 'buy'">买入</ElButton>
        <ElButton :type="txForm.type === 'sell' ? 'primary' : 'default'" @click="txForm.type = 'sell'">卖出</ElButton>
      </div>
      <ElForm :model="txForm" label-width="80px">
        <ElFormItem label="日期" required>
          <ElDatePicker
            v-model="txForm.date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </ElFormItem>
        <ElFormItem label="单价" required>
          <ElInputNumber v-model="txForm.price" :min="0.0001" :precision="4" style="width: 100%" />
        </ElFormItem>
        <ElFormItem label="金额" required>
          <ElInputNumber v-model="txForm.amount" :min="0.01" :precision="2" style="width: 100%" placeholder="投入金额" />
        </ElFormItem>
        <ElFormItem label="数量">
          <span class="computed-qty">{{ (txForm.price > 0 && txForm.amount > 0 ? txForm.amount / txForm.price : 0).toFixed(2) }}</span>
          <span class="qty-hint">（自动计算）</span>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="txDialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="txSubmitting" @click="submitTx">确定</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.holding-detail {
  max-width: 960px;
}

.holding-content {
  position: relative;
  min-height: 200px;
}

.header-row {
  margin-bottom: 16px;
}

.summary-card {
  margin-bottom: 16px;
}

.summary-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  margin-bottom: 16px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-item .label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.summary-item .value {
  font-size: 18px;
  font-weight: 600;
}

.summary-item .value.profit {
  color: #f56c6c;
}

.summary-item .value.loss {
  color: #67c23a;
}

.action-btns {
  display: flex;
  gap: 12px;
}

.chart-card {
  margin-bottom: 20px;
}

.chart-body {
  position: relative;
}

.chart-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.chart-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
}

.range-group {
  margin-left: auto;
}

.history-card {
  margin-bottom: 20px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-header .el-button {
  flex-shrink: 0;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
}

.history-item.buy {
  background: rgba(245, 108, 108, 0.1);
}

.history-item.sell {
  background: rgba(103, 194, 58, 0.1);
}

.history-item .type {
  font-weight: 500;
  min-width: 40px;
}

.history-item.buy .type {
  color: #f56c6c;
}

.history-item.sell .type {
  color: #67c23a;
}

.history-item .date {
  min-width: 100px;
}

.history-item .qty,
.history-item .price {
  min-width: 80px;
}

.history-item .amount {
  margin-left: auto;
  font-weight: 500;
}

@media (max-width: 768px) {
  .chart-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .range-group {
    margin-left: 0;
    width: 100%;
  }
}

.chart-container {
  width: 100%;
  height: 420px;
}

.error-tip,
.empty-tip {
  padding: 48px 0;
  text-align: center;
}

.tx-type-toggle {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.computed-qty {
  font-weight: 500;
  margin-right: 6px;
}

.qty-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
