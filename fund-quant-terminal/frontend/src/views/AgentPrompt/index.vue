<script setup lang="ts">
import { ref } from "vue";
import AgentRoleSetting from "./AgentRoleSetting.vue";
import ConnectionTest from "./ConnectionTest.vue";

const agent = ref<"grok" | "qwen">("grok");
</script>

<template>
  <div class="agent-prompt-wrapper">
    <div class="agent-role-setting-col">
      <AgentRoleSetting v-model:agent="agent" />
    </div>
    <div class="connection-test-col">
      <ConnectionTest :agent="agent" />
    </div>
  </div>
</template>

<style scoped>
.agent-prompt-wrapper {
  display: flex;
  gap: 20px;
  max-width: 1200px;
  align-items: flex-start;
}
.agent-role-setting-col { flex: 1; min-width: 0; }
.connection-test-col { flex: 0 0 560px; }
</style>