// =====================================================
// Grok / Agent 角色提示词 API
// =====================================================

import { request } from "./request";

/** Agent 角色模板（grok / qwen 多模板） */
export interface AgentTemplateItem {
  id: string;
  agent: string;
  name: string;
  content: string;
  updated_at: string;
  is_selected: boolean;
}

export const listAgentTemplates = (agent: string) =>
  request.get<{ data: { items: AgentTemplateItem[]; selected_id: string; primary_ai_agent: string } }>(
    "/agent-prompts",
    { params: { agent } }
  );

export const getPrimaryAgent = () =>
  request.get<{ data: { primary_ai_agent: string } }>("/agent-prompts/primary");

export const createAgentTemplate = (params: { agent: string; name: string; content: string }) =>
  request.post<{ data: { id: string; name: string; updated_at: string } }>("/agent-prompts", params);

export const updateAgentTemplate = (templateId: string, params: { name?: string; content?: string }) =>
  request.put("/agent-prompts/" + templateId, params);

export const deleteAgentTemplate = (templateId: string) =>
  request.delete("/agent-prompts/" + templateId);

export const selectAgentTemplate = (templateId: string) =>
  request.post("/agent-prompts/" + templateId + "/select");

/** 测试 Agent 连接：输入内容，返回 Agent 回复，不保存 */
export const agentChatTest = (agent: string, content: string) =>
  request.post<{ data: { ok: boolean; content: string } }>("/agent-prompts-test", {
    agent,
    content,
  });

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
