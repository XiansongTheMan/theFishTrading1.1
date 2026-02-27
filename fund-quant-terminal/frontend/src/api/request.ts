// =====================================================
// Axios 请求封装
// baseURL: http://localhost:8000/api
// 响应：成功返回 data，错误统一 ElMessage.error + 401/500/timeout 处理
// 请求：ElLoading 加载态（可通过 config.skipLoading 跳过，如 60s 自动刷新）
// =====================================================

import axios, { type InternalAxiosRequestConfig } from "axios";
import { ElLoading, ElMessage } from "element-plus";
import type { LoadingInstance } from "element-plus/es/components/loading/src/loading";

export const request = axios.create({
  baseURL: "http://localhost:8000/api",
  timeout: 15000,
});

export interface ApiResponse<T = unknown> {
  code: number;
  data: T;
  message: string;
}

declare module "axios" {
  interface AxiosRequestConfig {
    skipLoading?: boolean;
  }
  interface InternalAxiosRequestConfig {
    _loadingInstance?: LoadingInstance | null;
  }
}

function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const msg = (err.response?.data as { message?: string })?.message;
    if (msg) return msg;
    if (status === 401) return "未授权，请重新登录";
    if (status === 500) return "服务器错误";
    if (err.code === "ECONNABORTED") return "请求超时，请稍后重试";
    if (err.message?.toLowerCase().includes("network")) return "网络请求失败，请检查连接";
  }
  if (typeof err === "object" && err && "response" in err) {
    const ax = err as { response?: { data?: { message?: string }; status?: number } };
    const msg = ax.response?.data?.message;
    if (msg) return msg;
    const status = ax.response?.status;
    if (status === 401) return "未授权，请重新登录";
    if (status === 404) return "接口不存在";
    if (status === 500) return "服务器错误";
  }
  return "网络请求失败，请检查连接";
}

let loadingCount = 0;
let loadingInstance: LoadingInstance | null = null;

function showLoading(config: InternalAxiosRequestConfig): void {
  if (config.skipLoading) return;
  loadingCount++;
  if (loadingCount === 1 && !loadingInstance) {
    loadingInstance = ElLoading.service({
      lock: true,
      text: "加载中...",
      background: "rgba(0,0,0,0.4)",
    });
  }
}

function hideLoading(config: InternalAxiosRequestConfig): void {
  if (config.skipLoading) return;
  loadingCount = Math.max(0, loadingCount - 1);
  if (loadingCount === 0 && loadingInstance) {
    loadingInstance.close();
    loadingInstance = null;
  }
}

request.interceptors.request.use(
  (config) => {
    showLoading(config);
    return config;
  },
  (err) => Promise.reject(err)
);

request.interceptors.response.use(
  (res) => {
    hideLoading(res.config);
    const data = res.data as ApiResponse;
    if (data.code !== undefined && data.code !== 200) {
      const msg = data.message || "请求失败";
      if (!res.config.skipLoading) ElMessage.error(msg);
      const e = new Error(msg) as Error & { _toastShown?: boolean };
      e._toastShown = true;
      return Promise.reject(e);
    }
    return res.data;
  },
  (err) => {
    if (err?.config) hideLoading(err.config);
    const msg = getErrorMessage(err);
    // skipLoading 时不弹窗（如 60s 后台刷新），由调用方 try/catch 处理
    if (!err?.config?.skipLoading) {
      ElMessage.error(msg);
    }
    // 401: 未授权；500: 服务器错误；ECONNABORTED: 超时
    if (axios.isAxiosError(err)) {
      const status = err.response?.status;
      const code = err.code;
      if (status === 401) {
        // 可在此扩展：清除 token、跳转登录等
      }
      if (status === 500) {
        console.error("API 500:", err.response?.data);
      }
      if (code === "ECONNABORTED") {
        console.warn("API 请求超时");
      }
    } else {
      console.error("API Error:", err);
    }
    const e = err instanceof Error ? err : new Error(msg);
    (e as Error & { _toastShown?: boolean })._toastShown = true;
    return Promise.reject(e);
  }
);
