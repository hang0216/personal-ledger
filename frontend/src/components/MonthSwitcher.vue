<template>
  <div class="month-switcher">
    <el-button text aria-label="上一月" @click="step(-1)">◀</el-button>
    <el-date-picker
      :model-value="modelValue"
      type="month"
      value-format="YYYY-MM"
      format="YYYY-MM"
      placeholder="选择月份"
      :clearable="false"
      :disabled-date="disabledDate"
      style="width: 140px"
      @update:model-value="onPick"
    />
    <el-button text aria-label="下一月" @click="step(1)">▶</el-button>
  </div>
</template>

<script setup>
import { shiftMonth, currentMonth } from '@/utils/date'

const props = defineProps({
  modelValue: { type: String, required: true },
})
const emit = defineEmits(['update:modelValue'])

/** 不允许选择晚于当前月的月份（front-ui §2.2） */
function disabledDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}` > currentMonth()
}

function step(delta) {
  const next = shiftMonth(props.modelValue, delta)
  if (next > currentMonth()) return
  emit('update:modelValue', next)
}

function onPick(value) {
  if (!value) return
  if (value > currentMonth()) return
  emit('update:modelValue', value)
}
</script>

<style scoped>
.month-switcher {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>