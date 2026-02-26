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

export const getTokens = () =>
  request.get<{ data: { items: TokenItem[] } }>("/config/tokens");

export const updateTokens = (tokens: Record<string, string>) =>
  request.put("/config/tokens", { tokens });

export const testToken = (key: string, value?: string) =>
  request.post<{ data: { ok: boolean; message?: string } }>("/config/tokens/test", {
    key,
    value: value ?? undefined,
  });
