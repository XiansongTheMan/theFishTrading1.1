// =====================================================
// 璺敱閰嶇疆
// =====================================================

import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "Home",
    component: () => import("../views/HomeView.vue"),
    meta: { title: "棣栭〉" },
  },
  {
    path: "/data",
    name: "DataTerminal",
    component: () => import("../views/DataTerminalView.vue"),
    meta: { title: "鏁版嵁缁堢" },
  },
  {
    path: "/decisions",
    name: "DecisionLog",
    component: () => import("../views/DecisionLogView.vue"),
    meta: { title: "鍐崇瓥鏃ュ織" },
  },
  {
    path: "/curve",
    name: "AssetCurve",
    component: () => import("../views/AssetCurveView.vue"),
    meta: { title: "璧勪骇鏇茬嚎" },
  },
  {
    path: "/assets",
    name: "Assets",
    component: () => import("../views/AssetsView.vue"),
    meta: { title: "璧勪骇" },
  },
  {
    path: "/news",
    name: "News",
    component: () => import("../views/NewsView.vue"),
    meta: { title: "甯傚満璧勮", icon: "News" },
  },
  {
    path: "/holding/:assetType/:symbol",
    name: "HoldingDetail",
    component: () => import("../views/HoldingDetailView.vue"),
    meta: { title: "鎸佷粨璇︽儏" },
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
    meta: { title: "璁剧疆" },
  },
  {
    path: "/interfaces",
    name: "Interfaces",
    component: () => import("../views/InterfacesView.vue"),
    meta: { title: "鎺ュ彛" },
  },
  {
    path: "/mongo-test",
    name: "MongoTest",
    component: () => import("../views/MongoTestView.vue"),
    meta: { title: "MongoDB 杩炴帴娴嬭瘯" },
  },
  {
    path: "/grok-prompt",
    name: "AgentPrompt",
    component: () => import("../views/AgentPrompt/index.vue"),
    meta: { title: "Agent 瑙掕壊璁惧畾" },
  },
  {
    path: "/wallstreet-test",
    name: "WallstreetTest",
    component: () => import("../views/WallstreetTestView.vue"),
    meta: { title: "鍗庡皵琛楄闂昏偂甯傛儏鎶ユ祴璇曡彍鍗曪紙渚?Grok 鍐崇瓥鍙傝€冿級" },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.afterEach((to) => {
  document.title = `${to.meta.title || "Fund Quant"} - 鍩洪噾閲忓寲缁堢`;
});

export default router;

