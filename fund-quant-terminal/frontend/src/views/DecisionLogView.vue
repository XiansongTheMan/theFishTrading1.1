<!--
  =====================================================
  决策日志 - 完整表单、表格、自动刷新
  =====================================================
-->
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import {
  ElCard,
  ElTable,
  ElTableColumn,
  ElTag,
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElSelect,
  ElOption,
  ElMessage,
  ElDivider,
} from "element-plus";
import * as echarts from "echarts";
import { logDecision, getDecisionList, deleteDecision, type DecisionLog } from "../api/decisions";
import { getAssetsSummary, updateAssets } from "../api/assets";
import { fetchGrokDecision, type GrokDecisionNewsItem } from "../api/grok";
import { useAppStore } from "../stores/app";
import { useChartResize } from "../composables/useChartResize";
import {
  fetchExportData,
  exportToExcel,
  exportToPdf,
} from "../utils/export";
import { withFeedback } from "../utils/feedback";

const appStore = useAppStore();
const list = ref<DecisionLog[]>([]);
const loading = ref(false);
const dialogVisible = ref(false);
const chartRef = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;
const REFRESH_INTERVAL = 60000; // 60秒自动刷新

const form = ref<Partial<DecisionLog>>({
  grok_prompt: "",
  grok_response: "",
  user_action: "hold",
  fund_code: "",
  amount_rmb: undefined,
  nav: undefined,
  fee: undefined,
  pnl: undefined,
  notes: "",
  capital_before: undefined,
  capital_after: undefined,
});

let refreshTimer: ReturnType<typeof setInterval> | null = null;

useChartResize(chartRef, () => chartInstance);

async function loadList(opts?: { skipLoading?: boolean }) {
  loading.value = true;
  try {
    const res = (await getDecisionList(undefined, { skipLoading: opts?.skipLoading })) as unknown as {
      data?: DecisionLog[];
    };
    list.value = Array.isArray(res?.data) ? res.data : [];
    renderPnlChart();
  } catch (e) {
    list.value = [];
    if (!opts?.skipLoading) console.warn("[DecisionLog] loadList 失败:", e);
  } finally {
    loading.value = false;
  }
}

async function refreshSummary() {
  try {
    const res = (await getAssetsSummary({ skipLoading: true })) as unknown as {
      data?: { capital: number; holdings: unknown[] };
    };
    const d = res?.data;
    if (d) {
      appStore.setCapital(d.capital);
      appStore.initFromAssets(
        (d.holdings ?? []) as { symbol: string; name: string; quantity: number; cost_price?: number; current_price?: number; asset_type: string; id?: string }[]
      );
    }
  } catch (e) {
    console.warn("[DecisionLog] 60s 刷新 refreshSummary 失败，下次重试:", e);
  }
}

function renderPnlChart() {
  if (!chartRef.value || list.value.length === 0) return;
  const withPnl = list.value.filter((r) => r.pnl != null);
  if (withPnl.length === 0 && chartInstance) {
    chartInstance.setOption({ xAxis: { data: [] }, series: [{ data: [] }] });
    return;
  }
  const dates = withPnl.map((r) => formatTimeShort(r.timestamp ?? r.created_at) ?? "");
  const pnls = withPnl.map((r) => r.pnl ?? 0);
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value);
  }
  chartInstance.setOption({
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: dates },
    yAxis: { type: "value", name: "盈亏(元)" },
    series: [{
      name: "盈亏",
      type: "bar",
      data: pnls.map((v) => ({ value: v, itemStyle: { color: v >= 0 ? "#67c23a" : "#f56c6c" } })),
    }],
  });
}

function formatTime(s?: string) {
  if (!s) return "-";
  try {
    return new Date(s).toLocaleString("zh-CN");
  } catch {
    return s;
  }
}

function formatTimeShort(s?: string) {
  if (!s) return "";
  try {
    const d = new Date(s);
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch {
    return s;
  }
}

function openAdd() {
  form.value = {
    grok_prompt: "",
    grok_response: "",
    user_action: "hold",
    fund_code: "",
    amount_rmb: undefined,
    nav: undefined,
    fee: undefined,
    pnl: undefined,
    notes: "",
    capital_before: appStore.totalAssets,
    capital_after: appStore.totalAssets,
  };
  dialogVisible.value = true;
}

const submitLogging = ref(false);
async function submitLog() {
  if (!form.value.fund_code?.trim()) {
    ElMessage.warning("请填写基金代码");
    return;
  }
  if (!form.value.user_action) {
    ElMessage.warning("请选择动作");
    return;
  }
  try {
    await withFeedback(submitLogging, async () => {
      await logDecision({
        grok_prompt: form.value.grok_prompt,
        grok_response: form.value.grok_response,
        user_action: form.value.user_action,
        fund_code: form.value.fund_code,
        amount_rmb: form.value.amount_rmb,
        nav: form.value.nav,
        fee: form.value.fee,
        pnl: form.value.pnl,
        notes: form.value.notes,
        capital_before: form.value.capital_before,
        capital_after: form.value.capital_after,
      });
      dialogVisible.value = false;

      if (form.value.user_action === "buy" || form.value.user_action === "sell") {
        const capAfter = form.value.capital_after ?? appStore.totalAssets;
        await updateAssets({ capital: capAfter });
      }

      loadList();
      refreshSummary();
    }, { success: "决策已保存" });
  } catch {
    ElMessage.error("提交失败");
  }
}

function copyLatestToClipboard() {
  const latest = list.value[0];
  if (!latest) {
    ElMessage.warning("暂无记录");
    return;
  }
  const text = `【Grok 输入】\n${latest.grok_prompt || "-"}\n\n【Grok 建议】\n${latest.grok_response || "-"}\n\n基金: ${latest.fund_code} | 动作: ${latest.user_action} | 盈亏: ${latest.pnl ?? "-"}`;
  navigator.clipboard.writeText(text).then(
    () => ElMessage.success("已复制到剪贴板，可粘贴给 Grok"),
    () => ElMessage.error("复制失败")
  );
}

const deleteLoading = ref<string | null>(null);
async function handleDelete(id: string) {
  if (deleteLoading.value) return;
  deleteLoading.value = id;
  try {
    await deleteDecision(id);
    ElMessage.success("已删除");
    loadList();
    refreshSummary();
  } catch {
    ElMessage.error("删除失败");
  } finally {
    deleteLoading.value = null;
  }
}

const exportLoading = ref(false);

// 一键收集资讯并生成 Grok 决策
const grokDecisionModalVisible = ref(false);
const grokDecisionLoading = ref(false);
const grokDecisionFundCode = ref("");
const grokDecisionPrompt = ref("");
const grokDecisionNews = ref<GrokDecisionNewsItem[]>([]);
async function openGrokDecisionModal() {
  grokDecisionModalVisible.value = true;
  grokDecisionFundCode.value = form.value.fund_code?.trim() || "";
  grokDecisionPrompt.value = "";
  grokDecisionNews.value = [];
  // 每次打开都清空，确保“刷新”语义
}
async function fetchGrokDecisionData() {
  const fc = grokDecisionFundCode.value.trim();
  if (!fc) {
    ElMessage.warning("请填写基金代码");
    return;
  }
  grokDecisionLoading.value = true;
  try {
    const res = (await fetchGrokDecision(fc, true)) as { data?: { prompt?: string; news_summary?: GrokDecisionNewsItem[] } };
    grokDecisionPrompt.value = res?.data?.prompt ?? "";
    grokDecisionNews.value = res?.data?.news_summary ?? [];
    ElMessage.success("已生成决策提示词");
  } catch {
    grokDecisionPrompt.value = "";
    grokDecisionNews.value = [];
  } finally {
    grokDecisionLoading.value = false;
  }
}
function copyGrokPromptToClipboard() {
  const text = grokDecisionPrompt.value;
  if (!text) {
    ElMessage.warning("暂无提示词可复制");
    return;
  }
  navigator.clipboard.writeText(text).then(
    () => ElMessage.success("已复制到剪贴板，可粘贴给 Grok"),
    () => ElMessage.error("复制失败")
  );
}
function fillGrokPromptToForm() {
  if (grokDecisionPrompt.value) {
    form.value.grok_prompt = grokDecisionPrompt.value;
    form.value.fund_code = grokDecisionFundCode.value.trim();
    grokDecisionModalVisible.value = false;
    ElMessage.success("已填入决策表单");
    dialogVisible.value = true;
  }
}
async function handleExportExcel() {
  exportLoading.value = true;
  try {
    const { summary, decisions } = await fetchExportData();
    exportToExcel(summary, decisions);
    ElMessage.success("Excel 已导出");
  } catch (e) {
    ElMessage.error((e as Error)?.message ?? "导出失败");
  } finally {
    exportLoading.value = false;
  }
}
async function handleExportPdf() {
  exportLoading.value = true;
  try {
    const { summary, decisions } = await fetchExportData();
    await exportToPdf(summary, decisions);
    ElMessage.success("PDF 已导出");
  } catch (e) {
    ElMessage.error((e as Error)?.message ?? "导出失败");
  } finally {
    exportLoading.value = false;
  }
}

onMounted(() => {
  loadList();
  refreshSummary();
  refreshTimer = setInterval(() => {
    loadList({ skipLoading: true });
    refreshSummary();
  }, REFRESH_INTERVAL);
  // 从 NewsView「保存为决策」跳转：填入 grok 提示并打开新增弹窗
  try {
    const raw = sessionStorage.getItem("grokPromptFromNews");
    if (raw) {
      sessionStorage.removeItem("grokPromptFromNews");
      const { grok_prompt, fund_code } = JSON.parse(raw) as { grok_prompt?: string; fund_code?: string };
      if (grok_prompt) {
        form.value.grok_prompt = grok_prompt;
        form.value.fund_code = fund_code ?? "";
        dialogVisible.value = true;
        ElMessage.success("已填入 Grok 提示词，请完善并提交");
      }
    }
  } catch {
    /* ignore */
  }
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<template>
  <div class="decision-log">
    <h2 class="page-title">决策日志</h2>

    <ElCard shadow="never">
      <div class="action-row">
        <ElButton type="primary" @click="openAdd">新增决策</ElButton>
        <ElButton type="success" @click="openGrokDecisionModal">一键收集资讯并生成Grok决策</ElButton>
        <ElButton @click="copyLatestToClipboard">复制最新记录</ElButton>
        <ElButton :loading="exportLoading" @click="handleExportExcel">导出 Excel</ElButton>
        <ElButton :loading="exportLoading" @click="handleExportPdf">导出 PDF</ElButton>
      </div>
      <div class="table-scroll-x" style="margin-top: 16px">
      <ElTable :data="list" v-loading="loading" stripe max-height="400">
        <ElTableColumn prop="timestamp" label="时间" width="160">
          <template #default="{ row }">{{ formatTime(row.timestamp ?? row.created_at) }}</template>
        </ElTableColumn>
        <ElTableColumn prop="grok_response" label="Grok 建议" min-width="160" show-overflow-tooltip />
        <ElTableColumn prop="user_action" label="动作" width="90">
          <template #default="{ row }">
            <ElTag :type="row.user_action === 'buy' ? 'success' : row.user_action === 'sell' ? 'danger' : 'info'">
              {{ row.user_action === "buy" ? "买入" : row.user_action === "sell" ? "卖出" : "持有" }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="fund_code" label="基金" width="90" />
        <ElTableColumn prop="amount_rmb" label="金额(元)" width="100">
          <template #default="{ row }">{{ row.amount_rmb != null ? row.amount_rmb : "-" }}</template>
        </ElTableColumn>
        <ElTableColumn prop="pnl" label="盈亏(元)" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.pnl != null && row.pnl < 0 ? '#f56c6c' : '#67c23a' }">
              {{ row.pnl != null ? row.pnl : "-" }}
            </span>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="capital_after" label="资金后" width="100">
          <template #default="{ row }">{{ row.capital_after != null ? row.capital_after : "-" }}</template>
        </ElTableColumn>
        <ElTableColumn prop="notes" label="备注" min-width="120" show-overflow-tooltip />
        <ElTableColumn label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <ElButton type="danger" link :loading="deleteLoading === row.id" :disabled="!!deleteLoading" @click="handleDelete(row.id!)">删除</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
      </div>
    </ElCard>

    <ElCard v-if="list.some((r) => r.pnl != null)" class="chart-card" shadow="never">
      <template #header>盈亏分布</template>
      <div ref="chartRef" class="chart"></div>
    </ElCard>

    <ElDialog
      v-model="grokDecisionModalVisible"
      title="一键收集资讯并生成Grok决策"
      width="680px"
      class="grok-decision-modal"
      @opened="grokDecisionPrompt = ''; grokDecisionNews = []"
    >
      <ElForm label-width="90px" label-position="top">
        <ElFormItem label="基金代码">
          <div class="grok-fund-row">
            <ElInput v-model="grokDecisionFundCode" placeholder="如 021896" style="width: 160px" />
            <ElButton type="primary" :loading="grokDecisionLoading" @click="fetchGrokDecisionData">生成</ElButton>
          </div>
        </ElFormItem>
      </ElForm>
      <div v-if="grokDecisionNews.length > 0" class="grok-news-section">
        <h4>相关资讯</h4>
        <div class="grok-news-cards">
          <div v-for="(item, i) in grokDecisionNews" :key="i" class="grok-news-card">
            <a v-if="item.link" :href="item.link" target="_blank" rel="noopener" class="news-title">{{ item.title || "(无标题)" }}</a>
            <span v-else class="news-title">{{ item.title || "(无标题)" }}</span>
            <p v-if="item.content_summary" class="news-summary">{{ item.content_summary }}</p>
            <span class="news-meta">{{ item.pub_date }} · {{ item.source || "RSS" }}</span>
          </div>
        </div>
      </div>
      <div v-if="grokDecisionPrompt" class="grok-prompt-section">
        <div class="grok-prompt-header">
          <h4>完整 Grok 提示词</h4>
          <ElButton type="primary" size="small" @click="copyGrokPromptToClipboard">复制提示词</ElButton>
        </div>
        <pre class="grok-prompt-text">{{ grokDecisionPrompt }}</pre>
        <ElButton type="success" plain size="small" @click="fillGrokPromptToForm">填入到决策表单</ElButton>
      </div>
      <template #footer>
        <ElButton @click="grokDecisionModalVisible = false">关闭</ElButton>
        <ElButton type="primary" :loading="grokDecisionLoading" @click="fetchGrokDecisionData">重新生成</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="dialogVisible" title="新增决策" width="520">
      <ElForm :model="form" label-width="110px">
        <ElFormItem label="基金代码">
          <ElInput v-model="form.fund_code" placeholder="如 000001" />
        </ElFormItem>
        <ElFormItem label="用户动作">
          <ElSelect v-model="form.user_action" style="width: 100%">
            <ElOption label="买入" value="buy" />
            <ElOption label="卖出" value="sell" />
            <ElOption label="持有" value="hold" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="Grok 输入">
          <ElInput v-model="form.grok_prompt" type="textarea" placeholder="发送给 Grok 的提示" :rows="2" />
        </ElFormItem>
        <ElFormItem label="Grok 建议">
          <ElInput v-model="form.grok_response" type="textarea" placeholder="Grok 的回复/建议" :rows="3" />
        </ElFormItem>
        <ElDivider />
        <ElFormItem label="交易金额(元)">
          <ElInputNumber v-model="form.amount_rmb" :min="0" :precision="2" style="width: 100%" />
        </ElFormItem>
        <ElFormItem label="净值">
          <ElInputNumber v-model="form.nav" :min="0" :precision="4" style="width: 100%" />
        </ElFormItem>
        <ElFormItem label="手续费(元)">
          <ElInputNumber v-model="form.fee" :min="0" :precision="2" style="width: 100%" />
        </ElFormItem>
        <ElFormItem label="盈亏(元)">
          <ElInputNumber v-model="form.pnl" :precision="2" style="width: 100%" />
        </ElFormItem>
        <ElFormItem label="交易前资金">
          <ElInputNumber v-model="form.capital_before" :min="0" :precision="2" style="width: 100%" />
        </ElFormItem>
        <ElFormItem label="交易后资金">
          <ElInputNumber v-model="form.capital_after" :min="0" :precision="2" style="width: 100%" />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="form.notes" type="textarea" placeholder="备注" :rows="2" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitLogging" @click="submitLog">提交</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.decision-log {
  max-width: 1200px;
}

.page-title {
  margin: 0 0 20px;
}

.chart-card {
  margin-top: 20px;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chart {
  width: 100%;
  height: 220px;
}

@media (max-width: 480px) {
  .chart {
    height: 180px;
  }
}

.grok-fund-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.grok-news-section {
  margin-top: 16px;
}
.grok-news-section h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #606266;
}
.grok-news-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 200px;
  overflow-y: auto;
}
.grok-news-card {
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fafafa;
  font-size: 13px;
}
.grok-news-card .news-title {
  font-weight: 500;
  color: #409eff;
  text-decoration: none;
  display: block;
  margin-bottom: 4px;
}
.grok-news-card .news-title:hover {
  text-decoration: underline;
}
.grok-news-card .news-summary {
  margin: 0 0 6px;
  color: #606266;
  line-height: 1.4;
  font-size: 12px;
}
.grok-news-card .news-meta {
  font-size: 11px;
  color: #909399;
}
.grok-prompt-section {
  margin-top: 16px;
}
.grok-prompt-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.grok-prompt-header h4 {
  margin: 0;
  font-size: 14px;
  color: #606266;
}
.grok-prompt-text {
  padding: 12px;
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 240px;
  overflow-y: auto;
  margin: 0 0 10px;
}
</style>
