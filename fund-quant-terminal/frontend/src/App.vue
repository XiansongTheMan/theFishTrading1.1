<!--
  =====================================================
  根组件
  =====================================================
-->
<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import LayoutSidebar from "./components/LayoutSidebar.vue";
import { startGlobalRefresh, stopGlobalRefresh } from "./utils/refresh";

onMounted(() => {
  startGlobalRefresh();
});

onUnmounted(() => {
  stopGlobalRefresh();
});
</script>

<template>
  <LayoutSidebar>
    <RouterView />
  </LayoutSidebar>
</template>
