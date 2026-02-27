// =====================================================
// 决策日志 API
// =====================================================

import { request } from "./request";

export interface DecisionLog {
  id?: string;
  timestamp?: string;
  created_at?: string;
  grok_prompt?: string;
  grok_response?: string;
  user_action: string;
  fund_code: string;
  amount_rmb?: number;
  nav?: number;
  fee?: number;
  pnl?: number;
  notes?: string;
  capital_before?: number;
  capital_after?: number;
}

export const logDecision = (data: Omit<DecisionLog, "id" | "created_at">) =>
  request.post<{ data: DecisionLog }>("/decisions/log", data);

export const getDecisionList = (
  params?: { limit?: number; skip?: number; fund_code?: string; user_action?: string },
  config?: { skipLoading?: boolean }
) =>
  request.get<{ data: DecisionLog[] }>("/decisions/list", {
    params,
    skipLoading: config?.skipLoading,
  });

export const deleteDecision = (id: string) =>
  request.delete(`/decisions/${id}`);
