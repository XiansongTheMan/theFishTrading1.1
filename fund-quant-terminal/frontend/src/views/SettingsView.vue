<!--
  =====================================================
  设置 - 深色模式、初始资金等
  =====================================================
-->
<script setup lang="ts">
import { ElCard, ElSwitch, ElForm, ElFormItem, ElInputNumber } from "element-plus";
import { useAppStore } from "../stores/app";

const appStore = useAppStore();
</script>

<template>
  <div class="settings-view">
    <h2 class="page-title">设置</h2>
    <ElCard shadow="never">
      <ElForm label-width="120px">
        <ElFormItem label="深色模式">
          <ElSwitch
            :model-value="appStore.darkMode"
            @update:model-value="(v: boolean | string | number) => appStore.setDarkMode(Boolean(v))"
          />
        </ElFormItem>
        <ElFormItem label="初始资金（元）">
          <ElInputNumber
            :model-value="appStore.initialCapital"
            disabled
            :min="0"
          />
          <span class="form-tip">初始资金为固定值 2000 元</span>
        </ElFormItem>
        <ElFormItem label="当前现金（元）">
          <ElInputNumber
            :model-value="appStore.capital"
            :min="0"
            :precision="2"
            @update:model-value="(v?: number) => appStore.setCapital(v ?? 0)"
          />
        </ElFormItem>
      </ElForm>
    </ElCard>
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 500px;
}

.page-title {
  margin: 0 0 20px;
}

.form-tip {
  margin-left: 12px;
  color: var(--el-text-color-secondary);
  font-size: 0.85rem;
}
</style>
