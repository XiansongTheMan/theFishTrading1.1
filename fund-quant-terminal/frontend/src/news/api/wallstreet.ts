// =====================================================
// 华尔街见闻 API（news 模块）
// =====================================================

import { request } from "@/api/request";

export type WallStreetCNType = "lives" | "articles" | "search" | "quote" | "keyword";

export interface WallStreetCNTestParams {
  type: WallStreetCNType;
  code?: string;
  keyword?: string;
  limit?: number;
  channel?: string;
  cursor?: number;
  save_to_db?: boolean;
}

export const wallstreetcnTest = (params: WallStreetCNTestParams) =>
  request.post("wallstreetcn/test", params, { skipLoading: true });
