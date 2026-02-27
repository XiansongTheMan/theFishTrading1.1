<!--
  =====================================================
  资产配置 - 修改现金、添加/编辑/删除股票与基金
  =====================================================
-->
<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  ElCard,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElSelect,
  ElOption,
  ElButton,
  ElTable,
  ElTableColumn,
  ElDialog,
  ElMessage,
  ElMessageBox,
  ElAlert,
} from "element-plus";
import { useRouter } from "vue-router";
import {
  getAssetsSummary,
  updateAssets,
  createAsset,
  updateAsset,
  deleteAsset,
  syncAssets,
  type Asset,
  type AssetsSummary,
} from "../api/assets";
import { getFundInfo, getStockInfo } from "../api/data";
import { useAppStore } from "../stores/app";
import { fetchExportData, exportToExcel, exportToPdf } from "../utils/export";
import { withFeedback } from "../utils/feedback";

const appStore = useAppStore();
const router = useRouter();
const loading = ref(false);
const summary = ref<AssetsSummary | null>(null);

// 现金编辑
const capitalEdit = ref(0);
const capitalSaving = ref(false);

// 添加新资产 - 基金模式：代码、初始持有金额、初始亏损
const addDialogVisible = ref(false);
const addSaving = ref(false);
const addForm = ref({
  asset_type: "fund" as string,
  symbol: "",
  initial_amount: 0,
  initial_loss: 0,
  // 股票模式保留
  name: "",
  quantity: 0,
  cost_price: undefined as number | undefined,
  current_price: undefined as number | undefined,
});

// 帮助弹窗
const helpDialogVisible = ref(false);

// 编辑资产
const editDialogVisible = ref(false);
const editSaving = ref(false);
const editForm = ref<Partial<Asset>>({});
const editingId = ref<string | null>(null);

async function loadSummary() {
  loading.value = true;
  try {
    const res = (await getAssetsSummary()) as { data?: AssetsSummary };
    summary.value = res?.data ?? null;
    if (summary.value) {
      capitalEdit.value = summary.value.capital;
      appStore.setCapital(summary.value.capital);
      appStore.initFromAssets(
        summary.value.holdings.map((h) => ({
          symbol: h.symbol,
          name: h.name,
          quantity: h.quantity,
          cost_price: h.cost_price,
          current_price: h.current_price,
          asset_type: h.asset_type ?? "fund",
          id: h.id,
        }))
      );
    }
  } catch {
    summary.value = null;
  } finally {
    loading.value = false;
  }
}

async function saveCapital() {
  try {
    await withFeedback(capitalSaving, async () => {
      await updateAssets({ capital: capitalEdit.value });
      appStore.setCapital(capitalEdit.value);
      await loadSummary();
    }, { success: "现金已保存" });
  } catch {
    ElMessage.error("保存失败");
  }
}

function openAddDialog() {
  addForm.value = {
    asset_type: "fund",
    symbol: "",
    initial_amount: 0,
    initial_loss: 0,
    name: "",
    quantity: 0,
    cost_price: undefined,
    current_price: undefined,
  };
  addDialogVisible.value = true;
}

function openHelp() {
  helpDialogVisible.value = true;
}

async function submitAdd() {
  const isFund = addForm.value.asset_type === "fund";
  const symbol = addForm.value.symbol.trim();
  if (!symbol) {
    ElMessage.warning("请填写基金/股票代码");
    return;
  }

  if (isFund) {
    const amount = addForm.value.initial_amount ?? 0;
    const loss = addForm.value.initial_loss ?? 0;
    if (amount < 0) {
      ElMessage.warning("初始持有金额不能为负");
      return;
    }
    if (loss < 0) {
      ElMessage.warning("初始亏损不能为负");
      return;
    }
  } else {
    if (!addForm.value.name?.trim()) {
      ElMessage.warning("请填写名称");
      return;
    }
    if ((addForm.value.quantity ?? 0) < 0) {
      ElMessage.warning("数量不能为负");
      return;
    }
  }

  try {
    await withFeedback(addSaving, async () => {
    if (isFund) {
      const res = (await getFundInfo(symbol)) as { data?: { name: string; nav: number } };
      const info = res?.data;
      if (!info?.nav || info.nav <= 0) {
        throw new Error("无法获取基金净值，请检查代码或在数据终端先行拉取");
      }
      const amount = addForm.value.initial_amount ?? 0;
      const loss = addForm.value.initial_loss ?? 0;
      const cost = amount + loss;
      const nav = info.nav;
      const quantity = amount > 0 && nav > 0 ? amount / nav : 0;
      const cost_price = quantity > 0 ? cost / quantity : nav;
      await createAsset({
        symbol,
        name: info.name || `基金${symbol}`,
        quantity,
        cost_price,
        current_price: nav,
        asset_type: "fund",
      });
    } else {
      // 获取股票真实名称，若无则使用用户输入
      let stockName = addForm.value.name?.trim();
      try {
        const stockRes = (await getStockInfo(symbol)) as { data?: { name?: string; latest_price?: number } };
        const realName = stockRes?.data?.name?.trim();
        if (realName && !realName.startsWith("股票" + symbol)) stockName = realName;
        if (stockRes?.data?.latest_price != null && addForm.value.current_price == null) {
          addForm.value.current_price = stockRes.data.latest_price;
        }
      } catch {
        /* 忽略，使用用户输入 */
      }
      await createAsset({
        symbol,
        name: stockName || addForm.value.name!.trim() || symbol,
        quantity: addForm.value.quantity ?? 0,
        cost_price: addForm.value.cost_price,
        current_price: addForm.value.current_price,
        asset_type: "stock",
      });
    }
    addDialogVisible.value = false;
    await loadSummary();
    }, { success: "添加成功" });
  } catch (e) {
    const msg = (e as Error)?.message || "添加失败";
    ElMessage.error(msg);
  }
}

async function openEditDialog(row: Asset) {
  editingId.value = row.id ?? null;
  editForm.value = {
    symbol: row.symbol,
    name: row.name,
    quantity: row.quantity,
    cost_price: row.cost_price,
    current_price: row.current_price,
    asset_type: row.asset_type,
  };
  editDialogVisible.value = true;
  // 获取真实名称并更新
  try {
    const sym = row.symbol?.trim().split(".")[0];
    if (!sym) return;
    if (row.asset_type === "stock") {
      const res = (await getStockInfo(sym)) as { data?: { name?: string; latest_price?: number } };
      if (res?.data?.name?.trim()) {
        editForm.value.name = res.data.name.trim();
        if (res.data.latest_price != null && editForm.value.current_price == null) {
          editForm.value.current_price = res.data.latest_price;
        }
      }
    } else {
      const res = (await getFundInfo(sym)) as { data?: { name?: string; nav?: number } };
      if (res?.data?.name?.trim()) {
        editForm.value.name = res.data.name.trim();
        if (res.data.nav != null && editForm.value.current_price == null) {
          editForm.value.current_price = res.data.nav;
        }
      }
    }
  } catch {
    /* 忽略，保留原值 */
  }
}

async function submitEdit() {
  if (!editingId.value || !editForm.value.symbol?.trim() || !editForm.value.name?.trim()) {
    ElMessage.warning("请填写代码和名称");
    return;
  }
  try {
    await withFeedback(editSaving, async () => {
      await updateAsset(editingId.value!, {
        symbol: editForm.value.symbol!.trim(),
        name: editForm.value.name!.trim(),
        quantity: editForm.value.quantity ?? 0,
        cost_price: editForm.value.cost_price,
        current_price: editForm.value.current_price,
        asset_type: editForm.value.asset_type ?? "fund",
      });
      editDialogVisible.value = false;
      await loadSummary();
    }, { success: "资产已更新" });
  } catch {
    ElMessage.error("修改失败");
  }
}

const deleteLoading = ref<string | null>(null);
async function handleDelete(row: Asset) {
  if (!row.id || deleteLoading.value) return;
  try {
    await ElMessageBox.confirm(`确定删除 ${row.name}（${row.symbol}）？`, "确认删除", {
      type: "warning",
    });
  } catch {
    return;
  }
  deleteLoading.value = row.id;
  try {
    await deleteAsset(row.id);
    ElMessage.success("已删除");
    await loadSummary();
  } catch {
    ElMessage.error("删除失败");
  } finally {
    deleteLoading.value = null;
  }
}

function marketValue(row: Asset) {
  const price = row.current_price ?? row.cost_price ?? 0;
  return (row.quantity * price).toFixed(2);
}

function currentProfit(row: Asset) {
  const curr = row.current_price;
  const cost = row.cost_price ?? 0;
  if (curr == null || row.quantity == null) return "-";
  const profit = (curr - cost) * row.quantity;
  return profit >= 0 ? `+${profit.toFixed(2)}` : profit.toFixed(2);
}

function goToDetail(row: Asset) {
  const sym = row.symbol?.trim().split(".")[0];
  const type = row.asset_type === "stock" ? "stock" : "fund";
  if (sym) router.push(`/holding/${type}/${encodeURIComponent(sym)}`);
}

const syncLoading = ref(false);
const exportLoading = ref(false);
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
async function handleSync() {
  try {
    await withFeedback(syncLoading, async () => {
      const res = (await syncAssets()) as { data?: { updated?: number; failed?: number; total?: number } };
      const d = res?.data;
      await loadSummary();
      return d;
    }, {
      success: (d) => d ? `同步完成：成功 ${d.updated ?? 0}，失败 ${d.failed ?? 0}` : "数据已刷新",
    });
  } catch {
    ElMessage.error("同步失败");
  }
}

onMounted(loadSummary);
</script>

<template>
  <div class="assets-view">
    <h2 class="page-title">资产配置</h2>

    <!-- 现金配置 -->
    <ElCard shadow="never" class="card">
      <template #header>现金</template>
      <ElForm label-width="100px" inline>
        <ElFormItem label="全部现金（元）">
          <ElInputNumber
            v-model="capitalEdit"
            :min="0"
            :precision="2"
            placeholder="输入现金金额"
          />
        </ElFormItem>
        <ElFormItem>
          <ElButton type="primary" :loading="capitalSaving" @click="saveCapital">
            保存
          </ElButton>
        </ElFormItem>
      </ElForm>
    </ElCard>

    <!-- 添加新资产 -->
    <ElCard shadow="never" class="card">
      <template #header>
        <span>添加股票/基金</span>
        <ElButton type="primary" size="small" @click="openAddDialog">
          新增
        </ElButton>
      </template>
      <p class="tip">点击「新增」添加您的股票或基金持仓</p>
    </ElCard>

    <!-- 持仓列表 -->
    <ElCard shadow="never" class="card">
      <template #header>
        <span>当前持仓</span>
        <ElButton type="primary" size="small" :loading="syncLoading" @click="handleSync" style="margin-left: 12px">
          同步
        </ElButton>
        <ElButton size="small" :loading="exportLoading" @click="handleExportExcel" style="margin-left: 8px">
          导出 Excel
        </ElButton>
        <ElButton size="small" :loading="exportLoading" @click="handleExportPdf" style="margin-left: 8px">
          导出 PDF
        </ElButton>
      </template>
      <div class="table-scroll-x">
      <ElTable
        :data="summary?.holdings ?? []"
        v-loading="loading"
        stripe
        style="cursor: pointer"
        @row-click="goToDetail"
      >
        <ElTableColumn prop="symbol" label="代码" width="100" />
        <ElTableColumn prop="name" label="名称" min-width="120" />
        <ElTableColumn prop="asset_type" label="类型" width="80">
          <template #default="{ row }">
            {{ row.asset_type === "stock" ? "股票" : "基金" }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="quantity" label="数量" width="100" align="right">
          <template #default="{ row }">
            {{ row.quantity != null ? Math.round(row.quantity) : "-" }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="当前收益" width="100" align="right">
          <template #default="{ row }">
            {{ currentProfit(row) }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="current_price" label="现价" width="100" align="right">
          <template #default="{ row }">
            {{ row.current_price != null ? row.current_price.toFixed(4) : "-" }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="总资金" width="100" align="right">
          <template #default="{ row }">
            {{ marketValue(row) }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <ElButton type="primary" link size="small" @click.stop="openEditDialog(row)">
              编辑
            </ElButton>
            <ElButton type="danger" link size="small" :loading="deleteLoading === row.id" :disabled="!!deleteLoading" @click.stop="handleDelete(row)">
              删除
            </ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
      </div>
      <div v-if="!loading && (!summary?.holdings?.length)" class="empty-tip">
        暂无持仓，请点击上方「新增」添加
      </div>
      <div v-if="summary" class="summary-row">
        <span>持仓市值：{{ summary.holdings_value?.toFixed(2) ?? "0.00" }} 元</span>
        <span>总资产：{{ summary.total_value?.toFixed(2) ?? "0.00" }} 元</span>
      </div>
    </ElCard>

    <!-- 新增弹窗 -->
    <ElDialog v-model="addDialogVisible" title="添加股票/基金" width="480px">
      <template #header>
        <span>添加股票/基金</span>
        <ElButton type="info" link size="small" @click="openHelp" style="margin-left: 8px">
          ？帮助
        </ElButton>
      </template>
      <ElForm :model="addForm" label-width="120px">
        <ElFormItem label="类型">
          <ElSelect v-model="addForm.asset_type">
            <ElOption label="基金" value="fund" />
            <ElOption label="股票" value="stock" />
          </ElSelect>
        </ElFormItem>

        <!-- 基金模式 -->
        <template v-if="addForm.asset_type === 'fund'">
          <ElFormItem label="基金代码" required>
            <ElInput v-model="addForm.symbol" placeholder="如 000001、110011" />
          </ElFormItem>
          <ElFormItem label="初始持有金额（元）">
            <ElInputNumber
              v-model="addForm.initial_amount"
              :min="0"
              :precision="2"
              placeholder="0 表示仅添加关注"
              style="width: 100%"
            />
          </ElFormItem>
          <ElFormItem label="初始亏损（元）">
            <ElInputNumber
              v-model="addForm.initial_loss"
              :min="0"
              :precision="2"
              placeholder="已亏损金额，无亏损填 0"
              style="width: 100%"
            />
          </ElFormItem>
          <ElAlert type="info" :closable="false" show-icon style="margin-bottom: 12px">
            基金名称、份额、净值将由系统自动获取；填 0 表示仅添加关注、暂不持仓
          </ElAlert>
        </template>

        <!-- 股票模式 -->
        <template v-else>
          <ElFormItem label="股票代码" required>
            <ElInput v-model="addForm.symbol" placeholder="如 600519" />
          </ElFormItem>
          <ElFormItem label="名称" required>
            <ElInput v-model="addForm.name" placeholder="如 贵州茅台" />
          </ElFormItem>
          <ElFormItem label="数量" required>
            <ElInputNumber v-model="addForm.quantity" :min="0" :precision="2" />
          </ElFormItem>
          <ElFormItem label="成本价">
            <ElInputNumber v-model="addForm.cost_price" :min="0" :precision="4" />
          </ElFormItem>
          <ElFormItem label="现价">
            <ElInputNumber v-model="addForm.current_price" :min="0" :precision="4" />
          </ElFormItem>
        </template>
      </ElForm>
      <template #footer>
        <ElButton @click="addDialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="addSaving" @click="submitAdd">
          确定
        </ElButton>
      </template>
    </ElDialog>

    <!-- 帮助弹窗 -->
    <ElDialog v-model="helpDialogVisible" title="如何添加基金" width="520px">
      <div class="help-content">
        <h4>添加基金步骤：</h4>
        <ol>
          <li><strong>查找基金代码</strong>：前往「数据终端」页面，输入基金名称或代码搜索，或从基金列表中查看代码（如 000001、110011）</li>
          <li><strong>填写基金代码</strong>：在添加窗口中输入 6 位基金代码</li>
          <li><strong>初始持有金额</strong>：填写您当前持有的该基金的市值（元），即 份额 × 最新净值；填 0 表示仅添加关注</li>
          <li><strong>初始亏损</strong>：如已有亏损，填写亏损金额（元）；无亏损填 0</li>
        </ol>
        <p>系统将自动获取基金名称与最新净值，并计算份额与成本价。</p>
        <ElButton type="primary" size="small" @click="helpDialogVisible = false">
          知道了
        </ElButton>
      </div>
    </ElDialog>

    <!-- 编辑弹窗 -->
    <ElDialog v-model="editDialogVisible" title="编辑持仓" width="460px">
      <ElForm :model="editForm" label-width="100px">
        <ElFormItem label="代码" required>
          <ElInput v-model="editForm.symbol" placeholder="如 000001" />
        </ElFormItem>
        <ElFormItem label="名称" required>
          <ElInput v-model="editForm.name" placeholder="如 华夏成长混合" />
        </ElFormItem>
        <ElFormItem label="类型">
          <ElSelect v-model="editForm.asset_type">
            <ElOption label="基金" value="fund" />
            <ElOption label="股票" value="stock" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="数量" required>
          <ElInputNumber v-model="editForm.quantity" :min="0" :precision="2" />
        </ElFormItem>
        <ElFormItem label="成本价">
          <ElInputNumber v-model="editForm.cost_price" :min="0" :precision="4" />
        </ElFormItem>
        <ElFormItem label="现价">
          <ElInputNumber v-model="editForm.current_price" :min="0" :precision="4" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="editDialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="editSaving" @click="submitEdit">
          保存
        </ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.assets-view {
  max-width: 960px;
}

.page-title {
  margin: 0 0 20px;
  color: var(--el-text-color-primary);
}

.card {
  margin-bottom: 20px;
}

.tip {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 0.9rem;
}

.empty-tip {
  padding: 24px;
  text-align: center;
  color: var(--el-text-color-secondary);
}

.summary-row {
  margin-top: 16px;
  display: flex;
  gap: 24px;
  font-size: 0.95rem;
  color: var(--el-text-color-primary);
}

.help-content {
  line-height: 1.7;
}
.help-content h4 { margin-top: 0; }
.help-content ol { padding-left: 20px; }
.help-content li { margin-bottom: 8px; }
</style>
