/**
 * 新浪财经 - 新闻源接口配置
 * 二级 Tab：国际、市场、其他、焦点、公司、宏观、两会、观点
 */

export interface SinaTypeOption {
  value: string;
  label: string;
  category: string;
}

export const typeOptions: SinaTypeOption[] = [
  { value: "international", label: "国际", category: "international" },
  { value: "market", label: "市场", category: "market" },
  { value: "other", label: "其他", category: "other" },
  { value: "focus", label: "焦点", category: "focus" },
  { value: "company", label: "公司", category: "company" },
  { value: "macro", label: "宏观", category: "macro" },
  { value: "lianghui", label: "两会", category: "lianghui" },
  { value: "opinion", label: "观点", category: "opinion" },
];

export const defaultTypeVal = "macro";