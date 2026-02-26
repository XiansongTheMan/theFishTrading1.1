<!--
  =====================================================
  布局组件
  顶部导航 + 侧边栏 + 内容区
  =====================================================
-->
<script setup lang="ts">
import { ElContainer, ElHeader, ElMain, ElMenu, ElMenuItem } from "element-plus";
import { useRoute } from "vue-router";

const route = useRoute();
</script>

<template>
  <ElContainer class="layout">
    <ElHeader class="header">
      <div class="logo">Fund Quant Terminal</div>
      <ElMenu
        :default-active="route.path"
        mode="horizontal"
        :router="true"
        class="nav-menu"
      >
        <ElMenuItem index="/">仪表盘</ElMenuItem>
        <ElMenuItem index="/data">数据</ElMenuItem>
        <ElMenuItem index="/decisions">决策</ElMenuItem>
        <ElMenuItem index="/assets">资产</ElMenuItem>
      </ElMenu>
    </ElHeader>
    <ElMain class="main">
      <slot />
    </ElMain>
  </ElContainer>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  background: #1a1a2e;
  color: #eee;
  padding: 0 20px;
}

.logo {
  font-size: 1.2rem;
  font-weight: 600;
  margin-right: 40px;
}

.nav-menu {
  flex: 1;
  background: transparent;
  border: none;
}

.nav-menu :deep(.el-menu-item) {
  color: #ccc;
}

.nav-menu :deep(.el-menu-item.is-active) {
  color: #409eff;
}

.main {
  padding: 20px;
  background: #f5f7fa;
}
</style>
