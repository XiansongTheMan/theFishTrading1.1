/**
 * 新闻源配置注册表
 * 汇总各新闻源的子 Tab 配置，按 source 解耦
 */

import * as wallstreetcn from "./wallstreetcn";
import * as eastmoney from "./eastmoney";
import * as cailianshe from "./cailianshe";

export interface SourceOption {
  value: string;
  label: string;
}

export interface SourceConfig {
  typeOptions: Array<{
    value: string;
    label: string;
    type?: string;
    channel?: string;
    category?: string;
  }>;
  defaultTypeVal: string;
}

const configMap: Record<string, SourceConfig> = {
  wallstreetcn: {
    typeOptions: wallstreetcn.typeOptions,
    defaultTypeVal: wallstreetcn.defaultTypeVal,
  },
  eastmoney: {
    typeOptions: eastmoney.typeOptions,
    defaultTypeVal: eastmoney.defaultTypeVal,
  },
  cailianshe: {
    typeOptions: cailianshe.typeOptions,
    defaultTypeVal: cailianshe.defaultTypeVal,
  },
};

/** 一级 Tab - 新闻源选项 */
export const sourceOptions: SourceOption[] = [
  { value: "wallstreetcn", label: "华尔街见闻" },
  { value: "eastmoney", label: "东方财富" },
  { value: "cailianshe", label: "财联社" },
];

/** 根据新闻源获取子 Tab 配置 */
export function getSourceConfig(sourceVal: string): SourceConfig {
  const cfg = configMap[sourceVal];
  if (!cfg) {
    return configMap.wallstreetcn;
  }
  return cfg;
}