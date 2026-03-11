/**
 * 财联社 - 新闻源接口配置
 * 二级 Tab：加红、提醒、港美股、公司、基金、看板
 * 对应 RSSHub /cls/telegraph/:category
 */

export interface CailiansheTypeOption {
  value: string;
  label: string;
  category: string;
}

/** 财联社 - 接口类型选项（二级 Tab） */
export const typeOptions: CailiansheTypeOption[] = [
  { value: "red", label: "加红", category: "red" },
  { value: "remind", label: "提醒", category: "remind" },
  { value: "hk", label: "港美股", category: "hk" },
  { value: "announcement", label: "公司", category: "announcement" },
  { value: "fund", label: "基金", category: "fund" },
  { value: "watch", label: "看板", category: "watch" },
];

/** 默认选中的接口类型 */
export const defaultTypeVal = "red";
