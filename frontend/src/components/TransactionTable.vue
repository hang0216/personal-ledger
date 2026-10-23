<template>
  <el-table :data="rows" v-loading="loading" border stripe style="width: 100%">
    <el-table-column prop="date" label="日期" width="130" />
    <el-table-column label="类型" width="90">
      <template #default="{ row }">
        <el-tag :type="row.type === 'income' ? 'success' : 'danger'" disable-transitions>
          {{ typeLabel(row.type) }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="分类" width="140">
      <template #default="{ row }">{{ categoryName(row.category_id) }}</template>
    </el-table-column>
    <el-table-column label="金额" width="150" align="right">
      <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
    </el-table-column>
    <el-table-column label="备注" min-width="180" show-overflow-tooltip>
      <template #default="{ row }">{{ noteText(row.note) }}</template>
    </el-table-column>
    <el-table-column label="操作" width="140" align="center">
      <template #default="{ row }">
        <el-button link type="primary" @click="emit('edit', row)">编辑</el-button>
        <el-button link type="danger" @click="emit('delete', row)">删除</el-button>
      </template>
    </el-table-column>

    <template #empty>
      <EmptyState :text="emptyText">
        <el-button type="primary" @click="emit('empty-action')">{{ emptyActionText }}</el-button>
      </EmptyState>
    </template>
  </el-table>
</template>

<script setup>
import EmptyState from '@/components/EmptyState.vue'
import { formatMoney, noteText, typeLabel } from '@/utils/format'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  /** id → name 映射（接口列表不返回 category_name，front-ui §1.5） */
  categoryMap: { type: Object, default: () => ({}) },
  emptyText: { type: String, default: '本月暂无账单记录' },
  emptyActionText: { type: String, default: '＋ 记一笔' },
})
const emit = defineEmits(['edit', 'delete', 'empty-action'])

function categoryName(id) {
  return props.categoryMap?.[id] ?? '—'
}
</script>