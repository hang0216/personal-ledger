<template>
  <div class="pie-chart">
    <EmptyState v-if="!items.length" :text="emptyText" />
    <canvas v-show="items.length" ref="canvasRef" class="pie-chart__canvas" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArcElement, Chart, Legend, PieController, Tooltip } from 'chart.js'

import EmptyState from '@/components/EmptyState.vue'
import { pieColor } from '@/utils/format'

Chart.register(PieController, ArcElement, Tooltip, Legend)

const props = defineProps({
  /** expense_by_category：{ category_id, category_name, amount, percentage }[] */
  items: { type: Array, default: () => [] },
  emptyText: { type: String, default: '本月暂无数据' },
})

const canvasRef = ref(null)
let chart = null

function destroy() {
  if (chart) {
    chart.destroy()
    chart = null
  }
}

function render() {
  destroy()
  if (!props.items.length || !canvasRef.value) return
  chart = new Chart(canvasRef.value, {
    type: 'pie',
    data: {
      labels: props.items.map((item) => item.category_name),
      datasets: [
        {
          // 直接消费后端 percentage，前端不重算（spec §6.3、AC-12）
          data: props.items.map((item) => item.percentage),
          backgroundColor: props.items.map((_, index) => pieColor(index)),
          borderColor: '#ffffff',
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label} ${Number(ctx.parsed).toFixed(2)}%`,
          },
        },
      },
    },
  })
}

watch(() => props.items, render, { deep: true })
onMounted(render)
onBeforeUnmount(destroy)
</script>

<style scoped>
.pie-chart {
  height: 260px;
}

.pie-chart__canvas {
  height: 260px;
}
</style>