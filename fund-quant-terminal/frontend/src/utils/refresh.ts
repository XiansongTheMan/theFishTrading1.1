// =====================================================
// 全局数据刷新 - 60 秒间隔，断线重连
// =====================================================

import { getAssetsSummary } from "../api/assets";
import { request } from "../api/request";
import { useAppStore } from "../stores/app";

const REFRESH_INTERVAL_MS = 60 * 1000; // 60 秒
let refreshTimer: ReturnType<typeof setInterval> | null = null;

export function startGlobalRefresh() {
  if (refreshTimer) return;
  const appStore = useAppStore();

  async function doRefresh() {
    try {
      const res = (await getAssetsSummary({ skipLoading: true })) as unknown as {
        data?: { capital?: number; holdings?: unknown[] };
      };
      const d = res?.data;
      if (d) {
        if (d.capital != null) appStore.setCapital(d.capital);
        const arr = Array.isArray(d.holdings) ? d.holdings : [];
        if (arr.length) {
          appStore.initFromAssets(
            arr as {
              symbol: string;
              name: string;
              quantity: number;
              cost_price?: number;
              current_price?: number;
              asset_type: string;
              id?: string;
            }[]
          );
        }
      }
    } catch (e) {
      console.warn("[refresh] 60s 自动刷新失败，下次重试:", e);
    }
  }

  doRefresh();
  refreshTimer = setInterval(doRefresh, REFRESH_INTERVAL_MS);
}

export function stopGlobalRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

export async function checkConnection(): Promise<boolean> {
  try {
    await request.get("/assets/summary", { skipLoading: true });
    return true;
  } catch {
    return false;
  }
}
