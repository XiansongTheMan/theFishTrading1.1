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
import { useAppStore } from "../stores/app";

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

async function loadList() {
  loading.value = true;
  try {
    const res = (await getDecisionList()) as unknown as { data?: DecisionLog[] };
    list.value = Array.isArray(res?.data) ? res.data : [];
    renderPnlChart();
  } catch {
    list.value = [];
  } finally {
    loading.value = false;
  }
}

async function refreshSummary() {
  try {
    const res = (await getAssetsSummary()) as unknown as { data?: { capital: number; holdings: unknown[] } };
    const d = res?.data;
    if (d) {
      appStore.setCapital(d.capital);
      appStore.initFromAssets(
        (d.holdings ?? []) as { symbol: string; name: string; quantity: number; cost_price?: number; current_price?: number; asset_type: string; id?: string }[]
      );
    }
  } catch (e) {
    console.warn("[DecisionLog] refreshSummary 失败:", e);
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
    window.addEventListener("resize", () => chartInstance?.resize());
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
    ElMessage.success("提交成功");
    dialogVisible.value = false;

    if (form.value.user_action === "buy" || form.value.user_action === "sell") {
      const capAfter = form.value.capital_after ?? appStore.totalAssets;
      await updateAssets({ capital: capAfter });
    }

    loadList();
    refreshSummary();
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

async function handleDelete(id: string) {
  try {
    await deleteDecision(id);
    ElMessage.success("已删除");
    loadList();
    refreshSummary();
  } catch {
    ElMessage.error("删除失败");
  }
}

onMounted(() => {
  loadList();
  refreshSummary();
  refreshTimer = setInterval(() => {
    loadList();
    refreshSummary();
  }, REFRESH_INTERVAL);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<template>
  <div class="decision-log">
    <h2 class="page-title">决策日志</h2>

    <ElCard shadow="never">
      <ElButton type="primary" @click="openAdd">新增决策</ElButton>
      <ElButton @click="copyLatestToClipboard" style="margin-left: 8px">复制最新记录</ElButton>
      <ElTable :data="list" v-loading="loading" style="margin-top: 16px" stripe max-height="400">
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
            <ElButton type="danger" link @click="handleDelete(row.id!)">删除</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>

    <ElCard v-if="list.some((r) => r.pnl != null)" class="chart-card" shadow="never">
      <template #header>盈亏分布</template>
      <div ref="chartRef" style="height: 220px"></div>
    </ElCard>

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
        <ElButton type="primary" @click="submitLog">提交</ElButton>
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
</style>
