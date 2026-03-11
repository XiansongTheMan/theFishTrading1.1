<!--
  =====================================================
  AI 分析结果展示面板
  展示投资组合分析结果，支持深色模式、响应式布局
  =====================================================
-->
<script setup lang="ts">
import { computed } from "vue";
import {
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElButton,
  ElAlert,
} from "element-plus";
import { DocumentAdd } from "@element-plus/icons-vue";

const props = defineProps<{
  analysisResult?: {
    analysis?: {
      fund_code?: string;
      action?: string;
      amount?: number;
      stop_profit_price?: number | null;
      stop_loss_price?: number | null;
      confidence?: number;
      risk_level?: string;
      reason?: string;
      disclaimer?: string;
      error?: string;
      raw?: string;
    };
  } | null;
}>();

const emit = defineEmits<{
  (e: "apply-to-log"): void;
}>();

const analysis = computed(() => props.analysisResult?.analysis ?? null);
const hasError = computed(() => !!analysis.value?.error);

const actionLabel = computed(() => {
  const a = analysis.value?.action;
  if (!a) return "-";
  const map: Record<string, string> = {
    buy: "买入",
    sell: "卖出",
    hold: "持有",
  };
  return map[a.toLowerCase()] ?? a;
});

const riskLabel = computed(() => {
  const r = analysis.value?.risk_level;
  if (!r) return "-";
  const map: Record<string, string> = {
    low: "低",
    medium: "中",
    high: "高",
  };
  return map[r.toLowerCase()] ?? r;
});

function handleApply() {
  emit("apply-to-log");
}
</script>

<template>
  <ElCard shadow="never" class="analysis-result-card">
    <template #header>
      <span>AI 分析结果</span>
      <ElButton
        v-if="!hasError && analysis?.fund_code"
        type="primary"
        size="small"
        :icon="DocumentAdd"
        @click="handleApply"
        style="margin-left: 12px"
      >
        应用到决策日志
      </ElButton>
    </template>

    <ElAlert
      v-if="hasError"
      type="error"
      :title="analysis?.error ?? '分析失败'"
      :description="analysis?.raw"
      show-icon
      :closable="false"
    />

    <template v-else-if="analysis">
      <ElDescriptions :column="1" border size="default" class="analysis-desc">
        <ElDescriptionsItem label="基金代码">
          {{ analysis.fund_code ?? "-" }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="建议操作">
          {{ actionLabel }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="建议金额（元）">
          {{ analysis.amount != null ? analysis.amount.toFixed(2) : "-" }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="止盈价">
          {{ analysis.stop_profit_price != null ? analysis.stop_profit_price : "-" }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="止损价">
          {{ analysis.stop_loss_price != null ? analysis.stop_loss_price : "-" }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="置信度">
          {{ analysis.confidence != null ? `${analysis.confidence}%` : "-" }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="风险等级">
          {{ riskLabel }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="分析理由">
          <span class="reason-text">{{ analysis.reason ?? "-" }}</span>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="免责声明">
          <span class="disclaimer-text">{{ analysis.disclaimer ?? "-" }}</span>
        </ElDescriptionsItem>
      </ElDescriptions>
    </template>

    <div v-else class="empty-tip">暂无分析结果</div>
  </ElCard>
</template>

<style scoped>
.analysis-result-card {
  margin-top: 16px;
}

.analysis-desc {
  margin: 0;
}

.reason-text,
.disclaimer-text {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.9rem;
  line-height: 1.5;
}

.disclaimer-text {
  color: var(--el-text-color-secondary);
  font-size: 0.85rem;
}

.empty-tip {
  padding: 24px;
  text-align: center;
  color: var(--el-text-color-secondary);
}

@media (max-width: 768px) {
  .analysis-desc :deep(.el-descriptions__label) {
    width: 100px;
  }
}
</style>
