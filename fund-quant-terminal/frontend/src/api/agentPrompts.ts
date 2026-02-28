// Agent role prompts API - grok / qwen multi-templates

import { request } from "./request";

export interface AgentTemplateItem {
  id: string;
  agent: string;
  name: string;
  content: string;
  updated_at: string;
  is_selected: boolean;
}

export const listAgentTemplates = (agent: string) =>
  request.get<{
    data: {
      items: AgentTemplateItem[];
      selected_id: string;
      primary_ai_agent: string;
    };
  }>("/agent-prompts", { params: { agent } });

export const getPrimaryAgent = () =>
  request.get<{ data: { primary_ai_agent: string } }>("/agent-prompts/primary");

export const createAgentTemplate = (params: {
  agent: string;
  name: string;
  content: string;
}) => request.post<{ data: { id: string; name: string; updated_at: string } }>(
  "/agent-prompts",
  params
);

export const updateAgentTemplate = (
  templateId: string,
  params: { name?: string; content?: string }
) => request.put("/agent-prompts/" + templateId, params);

export const deleteAgentTemplate = (templateId: string) =>
  request.delete("/agent-prompts/" + templateId);

export const selectAgentTemplate = (templateId: string) =>
  request.post("/agent-prompts/" + templateId + "/select");
