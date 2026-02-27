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
  sentiment_score?: number;
}

export interface SentimentSummary {
  positive: number;
  neutral: number;
  negative: number;
  avg: number;
}

export interface NewsListResponse {
  items: NewsItem[];
  total: number;
  page: number;
  limit: number;
  sentiment_summary?: SentimentSummary;
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
    timeout: 30000,
  });

/** 新闻分页列表（供市场资讯页） */
export const getNewsList = (
  params?: {
    fund_code?: string;
    days?: number;
    keyword?: string;
    page?: number;
    limit?: number;
    refresh?: boolean;
  },
  config?: { skipLoading?: boolean }
) =>
  request.get<{ data: NewsListResponse }>("/news/list", {
    params: {
      fund_code: params?.fund_code || undefined,
      days: params?.days ?? 7,
      keyword: params?.keyword || undefined,
      page: params?.page ?? 1,
      limit: params?.limit ?? 20,
      refresh: params?.refresh ?? false,
    },
    timeout: 30000,
    skipLoading: config?.skipLoading,
  });

export interface SentimentTrendItem {
  date: string;
  avg_sentiment: number;
  count: number;
}

export const getSentimentTrend = (params: { fund_code?: string; days?: number }) =>
  request.get<{ data: { items: SentimentTrendItem[]; fund_code: string } }>("/news/sentiment-trend", {
    params: { fund_code: params.fund_code || "", days: params.days ?? 14 },
    timeout: 10000,
  });

export const batchGrok = (newsLinks: string[]) =>
  request.post<{ data: { prompt: string; news_summary?: { title: string; link: string; pub_date: string }[] } }>(
    "/news/batch-grok",
    { news_links: newsLinks }
  );
