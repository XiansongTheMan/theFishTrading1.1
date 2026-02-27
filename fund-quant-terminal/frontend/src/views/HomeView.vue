<!--
  =====================================================
  首页 - 资产总览
  初始 2000 元，无持仓
  =====================================================
-->
<script setup lang="ts">
import { onMounted, computed, ref } from "vue";
import {
  ElCard,
  ElRow,
  ElCol,
  ElStatistic,
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElSelect,
  ElOption,
  ElMessage,
} from "element-plus";
import { useRouter } from "vue-router";
import { useAppStore } from "../stores/app";
import { withFeedback } from "../utils/feedback";
import { getAssets, getAssetsSummary, createAsset } from "../api/assets";
import { getFundInfo, getStockInfo } from "../api/data";

const appStore = useAppStore();
const router = useRouter();
const dialogVisible = ref(false);
const addLoading = ref(false);
const form = ref({
  symbol: "",
  name: "",
  quantity: 0,
  cost_price: undefined as number | undefined,
  current_price: undefined as number | undefined,
  asset_type: "fund",
});

onMounted(async () => {
  try {
    const res = (await getAssetsSummary()) as unknown as { data?: { capital?: number; holdings?: unknown[] } };
    const d = res?.data;
    if (d) {
      if (d.capital != null) appStore.setCapital(d.capital);
      const arr = Array.isArray(d.holdings) ? d.holdings : [];
      if (arr.length) {
        appStore.initFromAssets(arr as { symbol: string; name: string; quantity: number; cost_price?: number; current_price?: number; asset_type: string; id?: string }[]);
      }
    } else {
      const r2 = (await getAssets()) as unknown as { data?: unknown[] };
      const arr = Array.isArray(r2?.data) ? r2.data : [];
      if (arr.length) appStore.initFromAssets(arr as { symbol: string; name: string; quantity: number; cost_price?: number; current_price?: number; asset_type: string; id?: string }[]);
    }
  } catch {
    // 保持默认
  }
});

async function submitAsset() {
  if (!form.value.symbol?.trim()) {
    ElMessage.warning("请填写代码");
    return;
  }
  const sym = form.value.symbol.trim();
  let name = form.value.name?.trim();
  try {
    await withFeedback(addLoading, async () => {
      if (form.value.asset_type === "fund") {
        const res = (await getFundInfo(sym)) as { data?: { name?: string; nav?: number } };
        const apiName = res?.data?.name?.trim();
        if (apiName && !apiName.startsWith("基金" + sym)) name = apiName;
        if (res?.data?.nav != null && form.value.current_price == null) {
          form.value.current_price = res.data.nav;
        }
      } else {
        const res = (await getStockInfo(sym)) as { data?: { name?: string; latest_price?: number } };
        const apiName = res?.data?.name?.trim();
        if (apiName && !apiName.startsWith("股票" + sym)) name = apiName;
        if (res?.data?.latest_price != null && form.value.current_price == null) {
          form.value.current_price = res.data.latest_price;
        }
      }
      if (!name) name = form.value.name?.trim() || sym;
      await createAsset({
        symbol: sym,
        name,
        quantity: form.value.quantity,
        cost_price: form.value.cost_price,
        current_price: form.value.current_price,
        asset_type: form.value.asset_type,
      });
      dialogVisible.value = false;
      const res = (await getAssetsSummary()) as unknown as { data?: { capital?: number; holdings?: unknown[] } };
      const d = res?.data;
      if (d) {
        if (d.capital != null) appStore.setCapital(d.capital);
        const arr = Array.isArray(d.holdings) ? d.holdings : [];
        if (arr.length) appStore.initFromAssets(arr as { symbol: string; name: string; quantity: number; cost_price?: number; current_price?: number; asset_type: string; id?: string }[]);
      }
    }, { success: "资产已添加" });
  } catch {
    ElMessage.error("添加失败");
  }
}

function openAddAsset() {
  form.value = { symbol: "", name: "", quantity: 0, cost_price: undefined, current_price: undefined, asset_type: "fund" };
  dialogVisible.value = true;
}

function goToDetail(row: { symbol?: string; assetType?: string }) {
  const sym = row.symbol?.trim().split(".")[0];
  const type = (row.assetType ?? "fund") === "stock" ? "stock" : "fund";
  if (sym) router.push(`/holding/${type}/${encodeURIComponent(sym)}`);
}

const totalAssets = computed(() => appStore.totalAssets);
const holdingsValue = computed(() => appStore.holdingsValue);
const cash = computed(() => appStore.capital);
</script>

<template>
  <div class="home-view">
    <h2 class="page-title">资产总览</h2>
    <ElRow :gutter="20">
      <ElCol :xs="24" :sm="12" :md="8">
        <ElCard shadow="hover" class="stat-card">
          <ElStatistic title="总资产（元）" :value="totalAssets" :precision="2" />
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :sm="12" :md="8">
        <ElCard shadow="hover" class="stat-card">
          <ElStatistic title="现金（元）" :value="cash" :precision="2" />
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :sm="12" :md="8">
        <ElCard shadow="hover" class="stat-card">
          <ElStatistic title="持仓市值（元）" :value="holdingsValue" :precision="2" />
        </ElCard>
      </ElCol>
    </ElRow>

    <ElCard class="holdings-card" shadow="never">
      <template #header>
        <span>当前持仓</span>
        <ElButton type="primary" size="small" style="float: right" @click="openAddAsset">
          添加资产
        </ElButton>
      </template>
      <div v-if="appStore.holdings.length === 0" class="empty-hint">
        暂无持仓，初始资金 {{ appStore.initialCapital }} 元
      </div>
      <div v-else class="table-scroll-x">
      <el-table
        :data="appStore.holdings"
        stripe
        style="cursor: pointer"
        @row-click="goToDetail"
      >
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="quantity" label="数量/份额" width="120">
          <template #default="{ row }">
            {{ row.quantity != null ? Math.round(row.quantity) : "-" }}
          </template>
        </el-table-column>
        <el-table-column prop="currentPrice" label="现价" width="100">
          <template #default="{ row }">
            {{ row.currentPrice != null ? Number(row.currentPrice).toFixed(4) : "-" }}
          </template>
        </el-table-column>
        <el-table-column label="市值" width="120">
          <template #default="{ row }">
            {{ ((row.currentPrice ?? row.costPrice ?? 0) * row.quantity).toFixed(2) }} 元
          </template>
        </el-table-column>
      </el-table>
      </div>
    </ElCard>

    <ElDialog v-model="dialogVisible" title="添加资产" width="400">
      <ElForm :model="form" label-width="90px">
        <ElFormItem label="代码">
          <ElInput v-model="form.symbol" placeholder="如 000001" />
        </ElFormItem>
        <ElFormItem label="名称">
          <ElInput v-model="form.name" placeholder="如 华夏成长" />
        </ElFormItem>
        <ElFormItem label="数量/份额">
          <ElInputNumber v-model="form.quantity" :min="0" :precision="2" style="width: 100%" />
        </ElFormItem>
        <ElFormItem label="成本价">
          <ElInputNumber v-model="form.cost_price" :min="0" :precision="4" style="width: 100%" />
        </ElFormItem>
        <ElFormItem label="现价">
          <ElInputNumber v-model="form.current_price" :min="0" :precision="4" style="width: 100%" />
        </ElFormItem>
        <ElFormItem label="类型">
          <ElSelect v-model="form.asset_type" style="width: 100%">
            <ElOption label="基金" value="fund" />
            <ElOption label="股票" value="stock" />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="addLoading" @click="submitAsset">确定</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.home-view {
  max-width: 900px;
}

.page-title {
  margin: 0 0 20px;
  font-size: 1.25rem;
}

.stat-card {
  margin-bottom: 20px;
}

.holdings-card {
  margin-top: 20px;
}

.empty-hint {
  color: var(--el-text-color-secondary);
  padding: 24px;
  text-align: center;
}
</style>
