// =====================================================
// 资产 API
// =====================================================

import { request } from "./request";

export interface Asset {
  id?: string;
  symbol: string;
  name: string;
  quantity: number;
  cost_price?: number;
  current_price?: number;
  asset_type: string;
  remark?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AssetsSummary {
  capital: number;
  holdings: Asset[];
  holdings_value: number;
  total_value: number;
}

export const getAssets = (params?: {
  limit?: number;
  skip?: number;
  symbol?: string;
  asset_type?: string;
}) => request.get<{ data: Asset[] }>("/assets", { params });

export const getAssetsSummary = () =>
  request.get<{ data: AssetsSummary }>("/assets/summary");

export const updateAssets = (data: {
  capital?: number;
  assets?: Partial<Asset>[];
}) => request.post("/assets/update", data);

export const createAsset = (data: Omit<Asset, "id" | "created_at" | "updated_at">) =>
  request.post<{ data: Asset }>("/assets", data);

export const updateAsset = (id: string, data: Omit<Asset, "id" | "created_at" | "updated_at">) =>
  request.put<{ data: Asset }>(`/assets/${id}`, data);

export const deleteAsset = (id: string) => request.delete(`/assets/${id}`);

export const syncAssets = () =>
  request.post<{ data: { updated: number; failed: number; total: number } }>("/assets/sync");

export const getHoldingHistory = (assetType: string, symbol: string) =>
  request.get<{ data: { data: { date: string; value: number }[]; symbol: string; source: string } }>(
    `/assets/history/${encodeURIComponent(assetType)}/${encodeURIComponent(symbol.trim().split(".")[0])}`
  );

export interface HoldingTransaction {
  id?: string;
  symbol: string;
  asset_type: string;
  date: string;
  type: "buy" | "sell";
  quantity: number;
  price: number;
  amount: number;
  created_at?: string;
}

export interface HoldingSummary {
  symbol: string;
  asset_type: string;
  name: string;
  quantity: number;
  cost_price: number;
  current_price: number;
  invested: number;
  market_value: number;
  profit: number;
  profit_rate: number;
}

export const getHoldingTransactions = (assetType: string, symbol: string) =>
  request.get<{ data: HoldingTransaction[] }>(
    `/assets/history/${encodeURIComponent(assetType)}/${encodeURIComponent(symbol.trim().split(".")[0])}/transactions`
  );

export const getHoldingSummary = (assetType: string, symbol: string) =>
  request.get<{ data: HoldingSummary }>(
    `/assets/history/${encodeURIComponent(assetType)}/${encodeURIComponent(symbol.trim().split(".")[0])}/summary`
  );

export const createTransaction = (data: {
  symbol: string;
  asset_type: string;
  date: string;
  type: "buy" | "sell";
  quantity: number;
  price: number;
  amount?: number;
}) =>
  request.post<{ data: HoldingTransaction }>("/assets/transactions", data);

export const deleteTransaction = (
  assetType: string,
  symbol: string,
  transactionId: string
) =>
  request.delete(
    `/assets/history/${encodeURIComponent(assetType)}/${encodeURIComponent(symbol.trim().split(".")[0])}/transactions/${encodeURIComponent(transactionId)}`
  );

export const clearHoldingTransactions = (assetType: string, symbol: string) =>
  request.post(
    `/assets/history/${encodeURIComponent(assetType)}/${encodeURIComponent(symbol.trim().split(".")[0])}/transactions/clear`
  );
