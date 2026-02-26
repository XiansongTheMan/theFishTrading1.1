// =====================================================
// 应用全局状态
// 资本、持仓、资产曲线历史、深色模式
// =====================================================

import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";

const STORAGE_KEY = "fund-quant-app";

export interface Holding {
  symbol: string;
  name: string;
  quantity: number;
  costPrice?: number;
  currentPrice?: number;
  assetType: string;
  id?: string;
}

export interface AssetHistoryPoint {
  date: string;
  value: number;
}

export const useAppStore = defineStore("app", () => {
  // 初始资金 2000 元，从 localStorage 恢复
  const initialCapital = 2000;
  const saved = (() => {
    try {
      const s = localStorage.getItem(STORAGE_KEY);
      return s ? JSON.parse(s) : {};
    } catch {
      return {};
    }
  })();
  const capital = ref((saved.capital as number) ?? initialCapital);

  // 持仓列表（与后端 assets 同步后的本地缓存）
  const holdings = ref<Holding[]>([]);

  // 资产曲线历史：总资产随时间变化
  const assetHistory = ref<AssetHistoryPoint[]>([
    { date: new Date().toISOString().split("T")[0] ?? "", value: initialCapital },
  ]);

  // 深色模式，从 localStorage 恢复
  const darkMode = ref(Boolean(saved.darkMode));

  // 计算：持仓市值总和
  const holdingsValue = computed(() => {
    return holdings.value.reduce((sum, h) => {
      const price = h.currentPrice ?? h.costPrice ?? 0;
      return sum + h.quantity * price;
    }, 0);
  });

  // 计算：总资产 = 现金 + 持仓市值（这里简化为 capital 存现金，holdings 为持仓；若 capital 表示总资产则直接用）
  const totalAssets = computed(() => {
    // capital 表示现金，总资产 = 现金 + 持仓市值
    return capital.value + holdingsValue.value;
  });

  function setCapital(v: number) {
    capital.value = v;
    appendHistory(totalAssets.value);
  }

  function setHoldings(list: Holding[]) {
    holdings.value = list;
    appendHistory(totalAssets.value);
  }

  function appendHistory(value: number) {
    const date = new Date().toISOString().split("T")[0] ?? "";
    const last = assetHistory.value[assetHistory.value.length - 1];
    if (last?.date === date) {
      assetHistory.value[assetHistory.value.length - 1] = { date, value };
    } else {
      assetHistory.value.push({ date, value });
    }
  }

  function toggleDarkMode() {
    darkMode.value = !darkMode.value;
  }

  function setDarkMode(v: boolean) {
    darkMode.value = v;
  }

  watch([capital, darkMode], () => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ capital: capital.value, darkMode: darkMode.value })
      );
    } catch {}
  });

  function initFromAssets(assets: { symbol: string; name: string; quantity: number; cost_price?: number; current_price?: number; asset_type: string; id?: string }[]) {
    holdings.value = assets.map((a) => ({
      symbol: a.symbol,
      name: a.name,
      quantity: a.quantity,
      costPrice: a.cost_price,
      currentPrice: a.current_price,
      assetType: a.asset_type ?? "fund",
      id: a.id,
    }));
    appendHistory(totalAssets.value);
  }

  return {
    initialCapital,
    capital,
    holdings,
    assetHistory,
    darkMode,
    holdingsValue,
    totalAssets,
    setCapital,
    setHoldings,
    appendHistory,
    toggleDarkMode,
    setDarkMode,
    initFromAssets,
  };
});
