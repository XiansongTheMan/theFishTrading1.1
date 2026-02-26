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
import { useAppStore } from "../stores/app";
import { getAssets, getAssetsSummary, createAsset } from "../api/assets";

const appStore = useAppStore();
const dialogVisible = ref(false);
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
  if (!form.value.symbol || !form.value.name) {
    ElMessage.warning("请填写代码和名称");
    return;
  }
  try {
    await createAsset({
      symbol: form.value.symbol,
      name: form.value.name,
      quantity: form.value.quantity,
      cost_price: form.value.cost_price,
      current_price: form.value.current_price,
      asset_type: form.value.asset_type,
    });
    ElMessage.success("添加成功");
    dialogVisible.value = false;
    const res = (await getAssetsSummary()) as unknown as { data?: { capital?: number; holdings?: unknown[] } };
    const d = res?.data;
    if (d) {
      if (d.capital != null) appStore.setCapital(d.capital);
      const arr = Array.isArray(d.holdings) ? d.holdings : [];
      if (arr.length) appStore.initFromAssets(arr as { symbol: string; name: string; quantity: number; cost_price?: number; current_price?: number; asset_type: string; id?: string }[]);
    }
  } catch {
    ElMessage.error("添加失败");
  }
}

function openAddAsset() {
  form.value = { symbol: "", name: "", quantity: 0, cost_price: undefined, current_price: undefined, asset_type: "fund" };
  dialogVisible.value = true;
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
      <el-table v-else :data="appStore.holdings" stripe>
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="quantity" label="数量/份额" width="120" />
        <el-table-column prop="currentPrice" label="现价" width="100" />
        <el-table-column label="市值" width="120">
          <template #default="{ row }">
            {{ ((row.currentPrice ?? row.costPrice ?? 0) * row.quantity).toFixed(2) }} 元
          </template>
        </el-table-column>
      </el-table>
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
        <ElButton type="primary" @click="submitAsset">确定</ElButton>
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
