// =====================================================
// Axios 请求封装
// baseURL: http://localhost:8000/api
// 错误时在顶部弹出提示
// =====================================================

import axios from "axios";
import { toast } from "../utils/toast";

export const request = axios.create({
  baseURL: "http://localhost:8000/api",
  timeout: 15000,
});

export interface ApiResponse<T = unknown> {
  code: number;
  data: T;
  message: string;
}

function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === "object" && err && "response" in err) {
    const ax = err as { response?: { data?: { message?: string }; status?: number } };
    const msg = ax.response?.data?.message;
    if (msg) return msg;
    const status = ax.response?.status;
    if (status === 404) return "接口不存在";
    if (status === 500) return "服务器错误";
  }
  return "网络请求失败，请检查连接";
}

request.interceptors.response.use(
  (res) => {
    const data = res.data as ApiResponse;
    if (data.code !== undefined && data.code !== 200) {
      const msg = data.message || "请求失败";
      toast.error(msg);
      return Promise.reject(new Error(msg));
    }
    return res.data;
  },
  (err) => {
    toast.error(getErrorMessage(err));
    console.error("API Error:", err);
    return Promise.reject(err);
  }
);
