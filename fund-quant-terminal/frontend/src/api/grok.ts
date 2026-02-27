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

export interface GrokDecisionParams {
  fund_code?: string;
  include_news?: boolean;
  news_links?: string[];
}

export const fetchGrokDecision = (
  params: GrokDecisionParams | string,
  includeNews = true
) => {
  const body: Record<string, unknown> =
    typeof params === "string"
      ? { fund_code: params, include_news: includeNews }
      : { fund_code: params.fund_code ?? "", include_news: params.include_news ?? includeNews };
  if (params && typeof params === "object" && Array.isArray(params.news_links)) {
    body.news_links = params.news_links;
  }
  return request.post<{ data: { prompt: string; news_summary?: GrokDecisionNewsItem[] } }>(
    "/grok-decision",
    body
  );
};
