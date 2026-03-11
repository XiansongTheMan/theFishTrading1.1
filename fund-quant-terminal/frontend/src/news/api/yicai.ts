// =====================================================
// 第一财经 API（news 模块）
// =====================================================

import { request } from "@/api/request";

export interface YicaiTestParams {
  limit?: number;
  save_to_db?: boolean;
}

export const yicaiTest = (params: YicaiTestParams) =>
  request.post("yicai/test", params, { skipLoading: true });
