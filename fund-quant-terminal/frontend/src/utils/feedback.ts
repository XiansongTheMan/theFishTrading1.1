// =====================================================
// 全局反馈：防重复提交 + ElMessage 成功提示
// 配合 ElButton :loading 使用，禁用期间防止双击
// =====================================================

import type { Ref } from "vue";
import { toast } from "./toast";

/**
 * 执行异步操作：loading 期间防重复提交，成功时提示
 * @param loading - 用于 ElButton :loading 的 ref
 * @param fn - 异步函数
 * @param options - { success?: string | ((result: T) => string) } 成功时提示，可为函数
 * @returns 若已 loading 则跳过，否则返回 fn 结果
 */
export async function withFeedback<T>(
  loading: Ref<boolean>,
  fn: () => Promise<T>,
  options?: { success?: string | ((result: T) => string) }
): Promise<T | undefined> {
  if (loading.value) return undefined;
  loading.value = true;
  try {
    const result = await fn();
    if (options?.success) {
      const msg = typeof options.success === "function" ? options.success(result) : options.success;
      toast.success(msg);
    }
    return result;
  } finally {
    loading.value = false;
  }
}
