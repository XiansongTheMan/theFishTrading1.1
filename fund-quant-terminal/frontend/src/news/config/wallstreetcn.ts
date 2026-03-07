/**
 * 华尔街见闻 - 新闻源接口配置
 * 子 Tab（接口类型）与 channel 映射，独立文件便于维护与解耦
 */

import type { WallStreetCNType } from "@/news/api/wallstreet";

export interface TypeOption {
  value: string;
  label: string;
  type: WallStreetCNType;
  channel?: string;
}

/** 华尔街见闻 - 接口类型选项（子 Tab） */
export const typeOptions: TypeOption[] = [
  { value: "lives:global-channel", label: "实时快讯", type: "lives", channel: "global-channel" },
  { value: "lives:a-stock-channel", label: "A股", type: "lives", channel: "a-stock-channel" },
  { value: "lives:goldc-channel", label: "黄金", type: "lives", channel: "goldc-channel" },
  { value: "lives:us-stock-channel", label: "美股", type: "lives", channel: "us-stock-channel" },
  { value: "lives:tech-channel", label: "科技", type: "lives", channel: "tech-channel" },
  { value: "lives:finance-bonds", label: "金融", type: "lives", channel: "bond-channel" },
  { value: "lives:oil-channel", label: "石油", type: "lives", channel: "oil-channel" },
  { value: "lives:bond-channel", label: "债券", type: "lives", channel: "bond-channel" },
  { value: "lives:forex-fx", label: "外汇", type: "lives", channel: "forex-channel" },
  { value: "lives:commodity-channel", label: "大宗", type: "lives", channel: "commodity-channel" },
  { value: "lives:hk-stock-channel", label: "港股", type: "lives", channel: "hk-stock-channel" },
  { value: "keyword", label: "关键词搜索", type: "keyword" },
];

/** 默认选中的接口类型 */
export const defaultTypeVal = "lives:global-channel";