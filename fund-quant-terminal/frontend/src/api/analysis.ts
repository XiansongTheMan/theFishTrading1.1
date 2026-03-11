// =====================================================
// 投资组合分析 API
// =====================================================

import { request } from "./request";

export interface AnalyzePortfolioResponse {
  analysis: {
    fund_code?: string;
    action?: "buy" | "sell" | "hold";
    amount?: number;
    stop_profit_price?: number | null;
    stop_loss_price?: number | null;
    confidence?: number;
    risk_level?: "low" | "medium" | "high";
    reason?: string;
    disclaimer?: string;
    error?: string;
    raw?: string;
  };
  raw_context?: Record<string, unknown>;
  timestamp?: string;
  model?: string;
  provider?: string;
}

export const analyzePortfolio = (params?: { user_id?: string; model_type?: string }) =>
  request.post<{ data: AnalyzePortfolioResponse }>("/analyze-portfolio", params ?? {});
