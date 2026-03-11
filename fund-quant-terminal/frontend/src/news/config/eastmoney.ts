/**
 * 东方财富 - 新闻源接口配置
 * 仅 7*24 全球直播一种类型
 */

export interface EastMoneyTypeOption {
  value: string;
  label: string;
  type: "live";
}

/** 东方财富 - 接口类型选项（仅 7*24 全球直播） */
export const typeOptions: EastMoneyTypeOption[] = [
  { value: "live:7x24", label: "7*24全球直播", type: "live" },
];

/** 默认选中的接口类型 */
export const defaultTypeVal = "live:7x24";
