// =====================================================
// 新浪财经 API（news 模块）
// =====================================================

import { request } from "@/api/request";

export interface SinaTestParams {
  category?: string;
  limit?: number;
  save_to_db?: boolean;
}

export const sinaTest = (params: SinaTestParams) =>
  request.post("sina/test", params, { skipLoading: true, timeout: 25000 });