// =====================================================
// Grok 角色提示词 API
// =====================================================

import { request } from "./request";

export interface GrokPromptDoc {
  id?: string;
  content: string;
  version: number;
  updated_at?: string;
}

export const getGrokPrompt = (version?: number) =>
  request.get<{ data: GrokPromptDoc | null }>("/grok-prompt", {
    params: version != null ? { version } : {},
  });

export const saveGrokPrompt = (content: string) =>
  request.post<{ data: { id: string; version: number; updated_at: string } }>(
    "/grok-prompt",
    { content }
  );

export const getGrokPromptHistory = () =>
  request.get<
    { data: { id: string; version: number; updated_at: string }[] }
  >("/grok-prompt/history");

export interface GrokDecisionNewsItem {
  title: string;
  link: string;
  pub_date: string;
  source: string;
  content_summary: string;
}

export const fetchGrokDecision = (fundCode: string, includeNews = true) =>
  request.post<{ data: { prompt: string; news_summary?: GrokDecisionNewsItem[] } }>(
    "/grok-decision",
    { fund_code: fundCode, include_news: includeNews }
  );
