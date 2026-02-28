// =====================================================
// 配置 API - Token 等
// =====================================================

import { request } from "./request";

export interface TokenItem {
  key: string;
  label: string;
  status?: "using" | "future";
  placeholder: string;
  value_masked: string;
  has_value: boolean;
}

export interface TushareItem {
  id: string;
  key: string;
  value_masked: string;
  remark: string;
  has_value: boolean;
  order: number;
  is_primary: boolean;
}

/** AI Agent Token 列表项（与 TushareItem 结构一致） */
export interface AiTokenItem extends TushareItem {
  key: "grok" | "qwen";
}

export const getTokens = () =>
  request.get<{
    data: {
      grok_list: AiTokenItem[];
      qwen_list: AiTokenItem[];
      primary_ai_agent: string;
      tushare_list: TushareItem[];
      primary_data_source?: string;
    };
  }>("/config/tokens");

export const updateTokens = (params: {
  primary_ai_agent?: string;
  primary_data_source?: string;
  tushare_list?: { token?: string | null; remark: string; keep_existing?: boolean }[];
  grok_list?: { token?: string | null; remark: string; keep_existing?: boolean }[];
  qwen_list?: { token?: string | null; remark: string; keep_existing?: boolean }[];
}) => request.put("/config/tokens", params);

/** 获取主要数据源配置及当前实际使用的数据源 */
export const getDataSource = () =>
  request.get<{ data: { primary: string; effective: string } }>("/config/data-source");

export const testToken = (key: string, value?: string, index?: number) =>
  request.post<{ data: { ok: boolean; message?: string } }>("/config/tokens/test", {
    key,
    value: value ?? undefined,
    index: index ?? undefined,
  });

/** 关注基金列表（定时新闻抓取） */
export const getWatchedFunds = () =>
  request.get<{ data: { fund_codes: string[] } }>("/config/watched-funds");

export const updateWatchedFunds = (fundCodes: string[]) =>
  request.put<{ data: { fund_codes: string[] } }>("/config/watched-funds", {
    fund_codes: fundCodes,
  });
