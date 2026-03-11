/**
 * 第一财经 - 新闻源接口配置
 * 二级 Tab：快讯（官方 RSS）
 */

export interface YicaiTypeOption {
  value: string;
  label: string;
}

/** 第一财经 - 接口类型选项（二级 Tab） */
export const typeOptions: YicaiTypeOption[] = [
  { value: "kuaixun", label: "快讯" },
];

/** 默认选中的接口类型 */
export const defaultTypeVal = "kuaixun";
