// =====================================================
// Axios 请求封装
// baseURL: http://localhost:8000/api
// =====================================================

import axios from "axios";

export const request = axios.create({
  baseURL: "http://localhost:8000/api",
  timeout: 15000,
});

export interface ApiResponse<T = unknown> {
  code: number;
  data: T;
  message: string;
}

request.interceptors.response.use(
  (res) => {
    const data = res.data as ApiResponse;
    if (data.code !== undefined && data.code !== 200) {
      return Promise.reject(new Error(data.message || "请求失败"));
    }
    return res.data;
  },
  (err) => {
    console.error("API Error:", err);
    return Promise.reject(err);
  }
);
