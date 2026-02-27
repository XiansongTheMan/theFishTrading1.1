// =====================================================
// 应用入口
// Vue 3 + Element Plus 全量注册 + 中文
// 错误/信息/成功提示统一在顶部弹出
// =====================================================

import { createApp } from "vue";
import ElementPlus from "element-plus";
import zhCn from "element-plus/dist/locale/zh-cn.mjs";
import "element-plus/dist/index.css";
import "element-plus/theme-chalk/dark/css-vars.css";

import App from "./App.vue";
import router from "./router";
import { createPinia } from "pinia";
import { toast } from "./utils/toast";

import "./style.css";

// 暗色模式：启动前应用，避免闪烁
(function initDarkMode() {
  try {
    const s = localStorage.getItem("fund-quant-app");
    const data = s ? JSON.parse(s) : {};
    if (data.darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  } catch {}
})();

// 全局错误捕获 - 未处理错误在顶部提示
function showError(msg: string) {
  toast.error(msg);
}

const app = createApp(App);
app.config.errorHandler = (err: unknown) => {
  const msg = err instanceof Error ? err.message : String(err);
  showError(msg || "发生未知错误");
};

window.addEventListener("unhandledrejection", (e) => {
  const err = e.reason;
  if (err && typeof err === "object" && (err as { _toastShown?: boolean })._toastShown) {
    e.preventDefault();
    return;
  }
  const msg =
    err instanceof Error
      ? err.message
      : typeof err === "object" && err && "message" in err
        ? String((err as { message: unknown }).message)
        : String(err ?? "请求失败");
  showError(msg || "发生未知错误");
  e.preventDefault();
});
app.use(createPinia());
app.use(router);
app.use(ElementPlus, { locale: zhCn });
app.mount("#app");
