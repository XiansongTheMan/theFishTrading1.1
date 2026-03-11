// =====================================================
// 财联社 API（news 模块）
// =====================================================

import { request } from "@/api/request";

export interface CailiansheTestParams {
  category?: string;
  limit?: number;
  save_to_db?: boolean;
}

export const cailiansheTest = (params: CailiansheTestParams) =>
  request.post("cailianshe/test", params, { skipLoading: true });
