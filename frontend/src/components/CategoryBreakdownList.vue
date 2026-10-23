<template>
  <ul class="breakdown">
    <li v-for="(item, index) in items" :key="item.category_id" class="breakdown__item">
      <span class="breakdown__dot" :style="{ backgroundColor: pieColor(index) }" />
      <span class="breakdown__name">{{ item.category_name }}</span>
      <span class="breakdown__amount">{{ formatMoney(item.amount) }}</span>
      <span class="breakdown__percent">{{ formatPercent(item.percentage) }}</span>
    </li>
  </ul>
</template>

<script setup>
import { formatMoney, formatPercent, pieColor } from '@/utils/format'

defineProps({
  /** expense_by_category，顺序与后端一致（按 amount 降序），前端不重排 */
  items: { type: Array, default: () => [] },
})
</script>

<style scoped>
.breakdown {
  margin: 0;
  padding: 0;
  list-style: none;
}

.breakdown__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 4px;
  font-size: 14px;
}

.breakdown__item + .breakdown__item {
  border-top: 1px solid var(--el-border-color-lighter);
}

.breakdown__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex: none;
}

.breakdown__name {
  flex: 1;
}

.breakdown__amount {
  color: var(--el-text-color-regular);
}

.breakdown__percent {
  width: 76px;
  text-align: right;
  color: var(--el-text-color-secondary);
}
</style>