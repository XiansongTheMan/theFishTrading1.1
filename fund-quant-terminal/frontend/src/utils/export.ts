// =====================================================
// 导出：Excel（xlsx）+ PDF（html2pdf）
// 包含：资产摘要 + 最新 10 条决策
// =====================================================

import * as XLSX from "xlsx";
import html2pdf from "html2pdf.js";
import { getAssetsSummary } from "../api/assets";
import { getDecisionList } from "../api/decisions";
import type { AssetsSummary } from "../api/assets";
import type { DecisionLog } from "../api/decisions";

const DECISION_LIMIT = 10;

export async function fetchExportData(): Promise<{
  summary: AssetsSummary | null;
  decisions: DecisionLog[];
}> {
  const [summaryRes, decisionsRes] = await Promise.all([
    getAssetsSummary({ skipLoading: true }),
    getDecisionList({ limit: DECISION_LIMIT }, { skipLoading: true }),
  ]);
  const summary = (summaryRes as { data?: AssetsSummary })?.data ?? null;
  const decisions = Array.isArray((decisionsRes as { data?: DecisionLog[] })?.data)
    ? (decisionsRes as { data: DecisionLog[] }).data
    : [];
  return { summary, decisions };
}

function formatTime(s?: string): string {
  if (!s) return "-";
  try {
    return new Date(s).toLocaleString("zh-CN");
  } catch {
    return String(s);
  }
}

function actionLabel(a: string): string {
  return a === "buy" ? "买入" : a === "sell" ? "卖出" : "持有";
}

export function exportToExcel(summary: AssetsSummary | null, decisions: DecisionLog[]): void {
  const wb = XLSX.utils.book_new();

  // Sheet 1: 资产摘要
  const summaryRows = [
    ["资产摘要", ""],
    ["现金（元）", summary?.capital ?? 0],
    ["持仓市值（元）", summary?.holdings_value ?? 0],
    ["总资产（元）", summary?.total_value ?? 0],
    [],
    ["持仓明细", ""],
    ["代码", "名称", "类型", "数量", "成本价", "现价", "市值"],
  ];
  for (const h of summary?.holdings ?? []) {
    const price = h.current_price ?? h.cost_price ?? 0;
    const mv = (h.quantity * price).toFixed(2);
    summaryRows.push([
      h.symbol,
      h.name,
      h.asset_type === "stock" ? "股票" : "基金",
      h.quantity,
      h.cost_price ?? "-",
      h.current_price ?? "-",
      mv,
    ]);
  }
  const ws1 = XLSX.utils.aoa_to_sheet(summaryRows);
  XLSX.utils.book_append_sheet(wb, ws1, "资产摘要");

  // Sheet 2: 决策日志
  const decisionRows = [
    ["时间", "动作", "基金", "金额(元)", "净值", "盈亏(元)", "Grok 建议", "备注"],
  ];
  for (const d of decisions) {
    decisionRows.push([
      formatTime(d.timestamp ?? d.created_at),
      actionLabel(d.user_action),
      d.fund_code ?? "",
      d.amount_rmb ?? "-",
      d.nav ?? "-",
      d.pnl ?? "-",
      (d.grok_response ?? "").slice(0, 80),
      d.notes ?? "",
    ]);
  }
  const ws2 = XLSX.utils.aoa_to_sheet(decisionRows);
  XLSX.utils.book_append_sheet(wb, ws2, "决策日志");

  const fn = `基金量化-${new Date().toISOString().slice(0, 10)}.xlsx`;
  XLSX.writeFile(wb, fn);
}

function buildPdfHtml(summary: AssetsSummary | null, decisions: DecisionLog[]): string {
  const rows = decisions
    .map(
      (d) => `
    <tr>
      <td>${formatTime(d.timestamp ?? d.created_at)}</td>
      <td>${actionLabel(d.user_action)}</td>
      <td>${(d.fund_code ?? "").replace(/</g, "&lt;")}</td>
      <td>${d.amount_rmb ?? "-"}</td>
      <td>${d.pnl ?? "-"}</td>
      <td>${d.capital_after ?? "-"}</td>
      <td>${((d.grok_response ?? "").slice(0, 50) + ((d.grok_response ?? "").length > 50 ? "…" : "")).replace(/</g, "&lt;")}</td>
    </tr>`
    )
    .join("");

  return `
<div style="font-family: 'Microsoft YaHei', sans-serif; font-size: 12px; padding: 16px;">
  <h1 style="font-size: 18px; margin-bottom: 16px;">基金量化终端 - 导出</h1>
  <p>导出时间：${new Date().toLocaleString("zh-CN")}</p>

  <h2 style="font-size: 14px; margin: 16px 0 8px; color: #303133;">资产摘要</h2>
  <div style="margin-bottom: 16px;">
    <span style="margin-right: 24px;">现金：¥${(summary?.capital ?? 0).toLocaleString()}</span>
    <span style="margin-right: 24px;">持仓市值：¥${(summary?.holdings_value ?? 0).toLocaleString()}</span>
    <span>总资产：¥${(summary?.total_value ?? 0).toLocaleString()}</span>
  </div>

  <h2 style="font-size: 14px; margin: 16px 0 8px; color: #303133;">最新 ${decisions.length} 条决策</h2>
  <table style="width: 100%; border-collapse: collapse; margin-bottom: 12px;">
    <thead><tr>
      <th style="border: 1px solid #dcdfe6; padding: 6px 10px; text-align: left; background: #f5f7fa;">时间</th>
      <th style="border: 1px solid #dcdfe6; padding: 6px 10px; text-align: left; background: #f5f7fa;">动作</th>
      <th style="border: 1px solid #dcdfe6; padding: 6px 10px; text-align: left; background: #f5f7fa;">基金</th>
      <th style="border: 1px solid #dcdfe6; padding: 6px 10px; text-align: left; background: #f5f7fa;">金额</th>
      <th style="border: 1px solid #dcdfe6; padding: 6px 10px; text-align: left; background: #f5f7fa;">盈亏</th>
      <th style="border: 1px solid #dcdfe6; padding: 6px 10px; text-align: left; background: #f5f7fa;">资金后</th>
      <th style="border: 1px solid #dcdfe6; padding: 6px 10px; text-align: left; background: #f5f7fa;">Grok 建议</th>
    </tr></thead>
    <tbody>${rows || "<tr><td colspan='7'>暂无记录</td></tr>"}</tbody>
  </table>
</div>`;
}

export async function exportToPdf(summary: AssetsSummary | null, decisions: DecisionLog[]): Promise<void> {
  const html = buildPdfHtml(summary, decisions);
  const opt = {
    margin: 10,
    filename: `基金量化-${new Date().toISOString().slice(0, 10)}.pdf`,
    image: { type: "jpeg", quality: 0.98 },
    html2canvas: { scale: 2 },
    jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
  };
  const el = document.createElement("div");
  el.innerHTML = html;
  el.style.position = "absolute";
  el.style.left = "-9999px";
  el.style.width = "210mm";
  document.body.appendChild(el);
  try {
    await html2pdf().set(opt).from(el).save();
  } finally {
    document.body.removeChild(el);
  }
}
