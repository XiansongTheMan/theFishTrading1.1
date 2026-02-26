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
