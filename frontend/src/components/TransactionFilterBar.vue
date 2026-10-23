<template>
  <div class="filter-block">
    <div class="filter-bar">
      <MonthSwitcher
        :model-value="month"
        @update:model-value="emit('update:month', $event)"
      />

      <el-select
        :model-value="type"
        placeholder="类型"
        style="width: 120px"
        @update:model-value="onTypeChange"
      >
        <el-option label="全部" value="" />
        <el-option label="收入" value="income" />
        <el-option label="支出" value="expense" />
      </el-select>

      <el-select
        :model-value="categoryId"
        placeholder="分类"
        clearable
        style="width: 160px"
        @update:model-value="emit('update:categoryId', $event)"
      >
        <el-option label="全部" value="" />
        <el-option
          v-for="item in categoryOptions"
          :key="item.id"
          :label="item.name"
          :value="item.id"
        />
      </el-select>

      <el-button @click="emit('reset')">重置</el-button>
      <el-button type="primary" @click="emit('create')">＋ 新增账单</el-button>
    </div>

    <div class="search-bar">
      <span class="search-bar__label">搜索</span>
      <el-date-picker
        v-model="draftRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        format="YYYY-MM-DD"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        :disabled-date="disabledDate"
        style="width: 260px"
      />
      <el-input
        v-model="draftKeyword"
        placeholder="备注关键词"
        clearable
        maxlength="100"
        style="width: 200px"
        @keyup.enter="submitSearch"
        @clear="submitSearch"
      />
      <el-button type="primary" @click="submitSearch">查询</el-button>
      <el-button :disabled="!searchActive" @click="clearSearch">清除搜索</el-button>
      <span class="search-bar__spacer" />
      <el-button :disabled="!rowsCount" @click="emit('export')">导出 CSV</el-button>
    </div>

    <div v-if="searchActive" class="search-bar__hint">
      当前为搜索模式：按日期范围 / 备注关键词跨月查询，月份选择不生效。
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

import MonthSwitcher from '@/components/MonthSwitcher.vue'
import { MIN_DATE, today } from '@/utils/date'

const props = defineProps({
  month: { type: String, required: true },
  type: { type: String, default: '' },
  categoryId: { type: [Number, String], default: '' },
  /** 全部分类，用于按类型联动过滤下拉项（front-ui §3.3） */
  categories: { type: Array, default: () => [] },
  /** 已生效的搜索条件（来自父组件的查询结果状态） */
  startDate: { type: String, default: '' },
  endDate: { type: String, default: '' },
  keyword: { type: String, default: '' },
  /** 当前列表条数，为 0 时禁用导出 */
  rowsCount: { type: Number, default: 0 },
})
const emit = defineEmits([
  'update:month',
  'update:type',
  'update:categoryId',
  'search',
  'clear-search',
  'reset',
  'create',
  'export',
])

/** 草稿值：只有点击「查询」或回车才提交，避免每次按键都请求 */
const draftRange = ref(toRange(props.startDate, props.endDate))
const draftKeyword = ref(props.keyword)

const categoryOptions = computed(() => {
  if (!props.type) return props.categories
  return props.categories.filter((item) => item.type === props.type)
})

const searchActive = computed(
  () => Boolean(props.startDate || props.endDate || props.keyword),
)

watch(
  () => [props.startDate, props.endDate, props.keyword],
  ([start, end, keyword]) => {
    draftRange.value = toRange(start, end)
    draftKeyword.value = keyword
  },
)

function toRange(start, end) {
  return start || end ? [start || '', end || ''] : []
}

/** 类型变化时，若已选分类不属于新类型则清空，避免选出矛盾筛选 */
function onTypeChange(value) {
  emit('update:type', value)
  if (!value) return
  const current = props.categories.find((item) => item.id === props.categoryId)
  if (current && current.type !== value) emit('update:categoryId', '')
}

function submitSearch() {
  const range = draftRange.value || []
  emit('search', {
    startDate: range[0] || '',
    endDate: range[1] || '',
    keyword: (draftKeyword.value || '').trim(),
  })
}

function clearSearch() {
  draftRange.value = []
  draftKeyword.value = ''
  emit('clear-search')
}

/** 日期范围限定在 [2000-01-01, 今天]（与账单日期口径一致） */
function disabledDate(date) {
  const text = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(
    date.getDate(),
  ).padStart(2, '0')}`
  return text < MIN_DATE || text > today()
}
</script>

<style scoped>
.filter-block {
  margin-bottom: 16px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding: 12px 16px;
  background: #ffffff;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
}

.search-bar__label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.search-bar__spacer {
  flex: 1;
}

.search-bar__hint {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
