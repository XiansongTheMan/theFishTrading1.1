// =====================================================
// 新闻 API
// =====================================================

import { request } from "./request";

export interface NewsItem {
  title?: string;
  link?: string;
  pub_date?: string;
  source?: string;
  content_summary?: string;
  fund_code?: string;
  created_at?: string;
}

export const fetchNews = (params?: {
  fund_code?: string;
  days?: number;
  refresh?: boolean;
}) =>
  request.get<{ data: NewsItem[] }>("/news/fetch", {
    params: {
      fund_code: params?.fund_code || undefined,
      days: params?.days ?? 7,
      refresh: params?.refresh ?? true,
    },
    timeout: 30000, // RSS 抓取可能较慢，放宽至 30 秒
  });
