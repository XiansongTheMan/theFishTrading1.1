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
