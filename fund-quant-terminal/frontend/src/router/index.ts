// =====================================================
// 路由配置
// =====================================================

import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "Home",
    component: () => import("../views/HomeView.vue"),
    meta: { title: "首页" },
  },
  {
    path: "/data",
    name: "DataTerminal",
    component: () => import("../views/DataTerminalView.vue"),
    meta: { title: "数据终端" },
  },
  {
    path: "/decisions",
    name: "DecisionLog",
    component: () => import("../views/DecisionLogView.vue"),
    meta: { title: "决策日志" },
  },
  {
    path: "/curve",
    name: "AssetCurve",
    component: () => import("../views/AssetCurveView.vue"),
    meta: { title: "资产曲线" },
  },
  {
    path: "/assets",
    name: "Assets",
    component: () => import("../views/AssetsView.vue"),
    meta: { title: "资产" },
  },
  {
    path: "/token",
    name: "Token",
    component: () => import("../views/TokenView.vue"),
    meta: { title: "Token" },
  },
  {
    path: "/settings",
    name: "Settings",
    component: () => import("../views/SettingsView.vue"),
    meta: { title: "设置" },
  },
  {
    path: "/mongo-test",
    name: "MongoTest",
    component: () => import("../views/MongoTestView.vue"),
    meta: { title: "MongoDB 连接测试" },
  },
  {
    path: "/grok-prompt",
    name: "GrokPrompt",
    component: () => import("../views/GrokPrompt.vue"),
    meta: { title: "Grok AI 角色设定" },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.afterEach((to) => {
  document.title = `${to.meta.title || "Fund Quant"} - 基金量化终端`;
});

export default router;
