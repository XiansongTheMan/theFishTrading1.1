<!--
  =====================================================
  侧边栏布局
  导航：首页、数据终端、决策日志、资产曲线、设置
  =====================================================
-->
<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute } from "vue-router";
import {
  ElContainer,
  ElAside,
  ElMain,
  ElMenu,
  ElMenuItem,
  ElSubMenu,
  ElConfigProvider,
} from "element-plus";
import zhCn from "element-plus/dist/locale/zh-cn.mjs";
import { useAppStore } from "../stores/app";

const route = useRoute();
const appStore = useAppStore();

const topMenuItems = [
  { path: "/", name: "首页", icon: "HomeFilled" },
  { path: "/data", name: "数据终端", icon: "DataLine" },
  { path: "/decisions", name: "决策日志", icon: "Document" },
  { path: "/curve", name: "资产曲线", icon: "TrendCharts" },
  { path: "/assets", name: "资产", icon: "Wallet" },
];

const settingsSubItems = [
  { path: "/settings", name: "通用" },
  { path: "/grok-prompt", name: "Grok AI 角色设定" },
  { path: "/token", name: "Token" },
  { path: "/mongo-test", name: "MongoDB 连接测试" },
];

const defaultOpeneds = computed(() =>
  settingsSubItems.some((i) => route.path === i.path || route.path.startsWith(i.path + "/"))
    ? ["settings"]
    : []
);

watch(
  () => appStore.darkMode,
  (isDark) => {
    if (isDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  },
  { immediate: true }
);
</script>

<template>
  <ElConfigProvider :locale="zhCn">
    <ElContainer class="layout-container" :class="{ dark: appStore.darkMode }">
      <ElAside class="sidebar" width="220px">
        <div class="logo">基金量化终端</div>
        <ElMenu
          :default-active="route.path"
          :default-openeds="defaultOpeneds"
          router
          class="sidebar-menu"
          background-color="var(--el-bg-color)"
          text-color="var(--el-text-color-primary)"
          active-text-color="var(--el-color-primary)"
        >
          <ElMenuItem
            v-for="item in topMenuItems"
            :key="item.path"
            :index="item.path"
          >
            <span>{{ item.name }}</span>
          </ElMenuItem>
          <ElSubMenu index="settings">
            <template #title>设置</template>
            <ElMenuItem
              v-for="item in settingsSubItems"
              :key="item.path"
              :index="item.path"
            >
              <span>{{ item.name }}</span>
            </ElMenuItem>
          </ElSubMenu>
        </ElMenu>
      </ElAside>
      <ElMain class="main-content">
        <slot />
      </ElMain>
    </ElContainer>
  </ElConfigProvider>
</template>

<style scoped>
.layout-container {
  min-height: 100vh;
}

.sidebar {
  background: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color);
  padding-top: 12px;
}

.logo {
  padding: 0 20px 20px;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.sidebar-menu {
  border-right: none;
}

.main-content {
  padding: 20px;
  background: var(--el-fill-color-light);
}

.layout-container.dark .main-content {
  background: var(--el-bg-color-page);
}

@media (max-width: 768px) {
  .sidebar {
    width: 64px !important;
  }

  .logo {
    font-size: 0.85rem;
    padding: 0 8px 16px;
  }
}
</style>
