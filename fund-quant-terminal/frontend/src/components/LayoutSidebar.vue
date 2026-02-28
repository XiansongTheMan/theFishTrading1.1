<!--
  =====================================================
  侧边栏布局
  导航：首页、数据终端、决策日志、资产曲线、设置
  =====================================================
-->
<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import { getDataSource } from "../api/config";
import {
  ElContainer,
  ElAside,
  ElMain,
  ElHeader,
  ElMenu,
  ElMenuItem,
  ElSubMenu,
  ElConfigProvider,
  ElTooltip,
  ElButton,
  ElDrawer,
  ElTag,
} from "element-plus";
import { Sunny, Moon, Fold } from "@element-plus/icons-vue";
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
  { path: "/news", title: "市场资讯", name: "市场资讯", icon: "News" },
];

const settingsSubItems = [
  { path: "/settings", name: "通用" },
  { path: "/interfaces", name: "接口" },
  { path: "/grok-prompt", name: "Agent 角色设定" },
  { path: "/token", name: "Token" },
  { path: "/mongo-test", name: "MongoDB 连接测试" },
];

const defaultOpeneds = computed(() =>
  settingsSubItems.some((i) => route.path === i.path || route.path.startsWith(i.path + "/"))
    ? ["settings"]
    : []
);

const drawerVisible = ref(false);
const isMobile = ref(false);
const MOBILE_BREAK = 768;

function checkMobile() {
  isMobile.value = window.innerWidth < MOBILE_BREAK;
}
onMounted(() => {
  checkMobile();
  window.addEventListener("resize", checkMobile);
});
onUnmounted(() => {
  window.removeEventListener("resize", checkMobile);
});

function closeDrawer() {
  drawerVisible.value = false;
}

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

watch(route, (r) => {
  closeDrawer();
  if (r.path !== "/token") fetchDataSource();
});

const dataSourceEffective = ref<string>("");
async function fetchDataSource() {
  try {
    const res = (await getDataSource()) as { data?: { effective?: string } };
    dataSourceEffective.value = res?.data?.effective || "tushare";
  } catch {
    dataSourceEffective.value = "tushare";
  }
}
let _dataSourceTimer: ReturnType<typeof setInterval> | null = null;
function onDataSourceUpdated() {
  fetchDataSource();
}
onMounted(() => {
  fetchDataSource();
  _dataSourceTimer = setInterval(fetchDataSource, 30000);
  window.addEventListener("data-source-updated", onDataSourceUpdated);
});
onUnmounted(() => {
  if (_dataSourceTimer) clearInterval(_dataSourceTimer);
  window.removeEventListener("data-source-updated", onDataSourceUpdated);
});
</script>

<template>
  <ElConfigProvider :locale="zhCn">
    <ElContainer class="layout-container" direction="vertical" :class="{ dark: appStore.darkMode }">
      <ElHeader class="app-header">
        <ElButton
          v-if="isMobile"
          :icon="Fold"
          circle
          text
          class="menu-toggle"
          @click="drawerVisible = true"
        />
        <span class="header-spacer" />
        <ElTooltip :content="appStore.darkMode ? '切换浅色' : '切换深色'" placement="bottom">
          <ElButton
            :icon="appStore.darkMode ? Sunny : Moon"
            circle
            text
            @click="appStore.toggleDarkMode()"
          />
        </ElTooltip>
      </ElHeader>
      <ElContainer class="body-row">
        <ElAside class="sidebar" :class="{ 'sidebar-hidden': isMobile }" width="220px">
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
            <ElMenuItem v-for="item in topMenuItems" :key="item.path" :index="item.path">
              <span>{{ item.name }}</span>
            </ElMenuItem>
            <ElSubMenu index="settings">
              <template #title>设置</template>
              <ElMenuItem v-for="item in settingsSubItems" :key="item.path" :index="item.path">
                <span>{{ item.name }}</span>
              </ElMenuItem>
            </ElSubMenu>
          </ElMenu>
          <div class="sidebar-footer">
            <span class="data-source-label">数据源：</span>
            <ElTag size="small" type="info">{{ dataSourceEffective || "tushare" }}</ElTag>
          </div>
        </ElAside>
        <ElDrawer
          v-model="drawerVisible"
          title="导航"
          direction="ltr"
          size="280px"
          :show-close="true"
          class="nav-drawer"
        >
          <div class="drawer-logo">基金量化终端</div>
          <ElMenu
            :default-active="route.path"
            :default-openeds="defaultOpeneds"
            router
            class="drawer-menu"
            background-color="transparent"
            text-color="var(--el-text-color-primary)"
            active-text-color="var(--el-color-primary)"
            @select="closeDrawer"
          >
            <ElMenuItem v-for="item in topMenuItems" :key="item.path" :index="item.path">
              <span>{{ item.name }}</span>
            </ElMenuItem>
            <ElSubMenu index="settings">
              <template #title>设置</template>
              <ElMenuItem v-for="item in settingsSubItems" :key="item.path" :index="item.path">
                <span>{{ item.name }}</span>
              </ElMenuItem>
            </ElSubMenu>
          </ElMenu>
        </ElDrawer>
        <ElMain class="main-content">
          <slot />
        </ElMain>
      </ElContainer>
    </ElContainer>
  </ElConfigProvider>
</template>

<style scoped>
.layout-container {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  height: 48px;
  padding: 0 16px;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
}

.header-spacer {
  flex: 1;
}

.body-row {
  flex: 1;
  min-height: 0;
}

.sidebar {
  position: relative;
  background: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color);
  padding-top: 12px;
  padding-bottom: 48px;
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

.sidebar-footer {
  position: absolute;
  bottom: 12px;
  left: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: var(--el-text-color-secondary);
}

.data-source-label {
  white-space: nowrap;
}

.main-content {
  padding: 12px;
  background: var(--el-fill-color-light);
}

@media (min-width: 768px) {
  .main-content {
    padding: 20px;
  }
}

.layout-container.dark .main-content {
  background: var(--el-bg-color-page);
}

.sidebar-hidden {
  display: none !important;
}

.menu-toggle {
  margin-right: 8px;
}

.drawer-logo {
  padding: 0 0 20px;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.drawer-menu {
  border: none;
}
</style>
