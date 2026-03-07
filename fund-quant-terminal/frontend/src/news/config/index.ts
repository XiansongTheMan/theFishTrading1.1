/**
 * 新闻源配置注册表
 * 汇总各新闻源的子 Tab 配置，按 source 解耦
 */

import * as wallstreetcn from "./wallstreetcn";

export interface SourceOption {
  value: string;
  label: string;
}

export interface SourceConfig {
  typeOptions: typeof wallstreetcn.typeOptions;
  defaultTypeVal: string;
}

const configMap: Record<string, SourceConfig> = {
  wallstreetcn: {
    typeOptions: wallstreetcn.typeOptions,
    defaultTypeVal: wallstreetcn.defaultTypeVal,
  },
};

/** 一级 Tab - 新闻源选项 */
export const sourceOptions: SourceOption[] = [
  { value: "wallstreetcn", label: "华尔街见闻" },
];

/** 根据新闻源获取子 Tab 配置 */
export function getSourceConfig(sourceVal: string): SourceConfig {
  const cfg = configMap[sourceVal];
  if (!cfg) {
    return configMap.wallstreetcn;
  }
  return cfg;
}