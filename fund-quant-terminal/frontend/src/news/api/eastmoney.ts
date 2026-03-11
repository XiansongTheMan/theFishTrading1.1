// =====================================================
// 东方财富 API（news 模块）
// =====================================================

import { request } from "@/api/request";

export interface EastMoneyTestParams {
  limit?: number;
  save_to_db?: boolean;
}

export const eastmoneyTest = (params: EastMoneyTestParams) =>
  request.post("eastmoney/test", params, { skipLoading: true });
