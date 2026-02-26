// =====================================================
// 全局提示 - 统一在顶部弹出
// =====================================================

import { ElMessage } from "element-plus";

const TOP_OFFSET = 20;

export const toast = {
  success(msg: string) {
    ElMessage.success({ message: msg, offset: TOP_OFFSET });
  },
  error(msg: string) {
    ElMessage.error({ message: msg, offset: TOP_OFFSET });
  },
  warning(msg: string) {
    ElMessage.warning({ message: msg, offset: TOP_OFFSET });
  },
  info(msg: string) {
    ElMessage.info({ message: msg, offset: TOP_OFFSET });
  },
};
