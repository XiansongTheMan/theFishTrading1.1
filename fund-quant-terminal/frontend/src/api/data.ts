// =====================================================
// 数据相关 API
// =====================================================

import { request } from "./request";

export const fetchData = (fundCode: string, dataType: "nav" | "list" | "info") =>
  request.post("/data/fetch", { fund_code: fundCode, data_type: dataType });

export const fetchHistory = (
  fundCode: string,
  params?: { start_date?: string; end_date?: string; limit?: number }
) => request.get("/data/history", { params: { fund_code: fundCode, ...params } });
