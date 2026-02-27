// =====================================================
// 图表自动 resize - 基于 ResizeObserver，适配移动端
// =====================================================

import { onUnmounted, watch, type Ref } from "vue";
import type { ECharts } from "echarts";

export function useChartResize(
  chartRef: Ref<HTMLElement | null>,
  getChart: () => ECharts | null
) {
  let observer: ResizeObserver | null = null;
  let observedEl: HTMLElement | null = null;

  function stopObserve() {
    if (observer && observedEl) {
      try {
        observer.unobserve(observedEl);
      } catch {}
      observer = null;
      observedEl = null;
    }
  }

  function startObserve(el: HTMLElement) {
    stopObserve();
    observer = new ResizeObserver(() => getChart()?.resize());
    observer.observe(el);
    observedEl = el;
  }

  watch(
    chartRef,
    (el) => {
      stopObserve();
      if (el) startObserve(el);
    },
    { immediate: true }
  );

  onUnmounted(stopObserve);
}
