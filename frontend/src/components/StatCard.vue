<template>
  <div class="stat-card">
    <div class="stat-card__title">{{ title }}</div>
    <div class="stat-card__value" :class="valueClass">{{ amountText }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import { formatMoney } from '@/utils/format'

const props = defineProps({
  title: { type: String, required: true },
  amount: { type: Number, default: 0 },
  /** 'income' 绿色 / 'expense' 红色 / 'balance' 正绿负红（front-ui §2.2） */
  tone: { type: String, default: 'income' },
})

const amountText = computed(() => formatMoney(props.amount))

const valueClass = computed(() => {
  if (props.tone === 'balance') {
    return Number(props.amount) < 0 ? 'stat-card__value--expense' : 'stat-card__value--income'
  }
  return `stat-card__value--${props.tone}`
})
</script>

<style scoped>
.stat-card {
  padding: 16px 20px;
  background: #ffffff;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
}

.stat-card__title {
  margin-bottom: 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.stat-card__value {
  font-size: 24px;
  font-weight: 600;
}

.stat-card__value--income {
  color: var(--el-color-success);
}

.stat-card__value--expense {
  color: var(--el-color-danger);
}
</style>