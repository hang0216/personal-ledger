<template>
  <section class="page">
    <h2 class="page__title">账单管理</h2>

    <TransactionFilterBar
      :month="month"
      :type="type"
      :category-id="categoryId"
      :categories="categories"
      :start-date="appliedSearch.startDate"
      :end-date="appliedSearch.endDate"
      :keyword="appliedSearch.keyword"
      :rows-count="rows.length"
      @update:month="month = $event"
      @update:type="type = $event"
      @update:category-id="categoryId = $event"
      @search="applySearch"
      @clear-search="clearSearch"
      @reset="resetFilter"
      @create="openCreate"
      @export="exportCsv"
    />

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      class="page__alert"
    >
      <template #default>
        <el-button link type="primary" @click="loadRows">重试</el-button>
      </template>
    </el-alert>

    <TransactionTable
      :rows="rows"
      :loading="loading"
      :category-map="categoryMap"
      :empty-text="emptyText"
      :empty-action-text="emptyActionText"
      @edit="openEdit"
      @delete="askDelete"
      @empty-action="onEmptyAction"
    />

    <div v-if="!loading && !error" class="page__footer">共 {{ rows.length }} 条记录</div>

    <TransactionFormDialog
      v-model="formVisible"
      :categories="categories"
      :record="editingRecord"
      @success="loadRows"
      @refresh-categories="loadCategories"
    />

    <ConfirmDialog
      v-model="confirmVisible"
      title="提示"
      :message="confirmMessage"
      :detail="confirmDetail"
      :loading="deleting"
      @confirm="confirmDelete"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { listCategories } from '@/api/categories'
import { deleteTransaction, listTransactions } from '@/api/transactions'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import TransactionFilterBar from '@/components/TransactionFilterBar.vue'
import TransactionFormDialog from '@/components/TransactionFormDialog.vue'
import TransactionTable from '@/components/TransactionTable.vue'
import { downloadCsv, toCsv } from '@/utils/csv'
import { currentMonth, today } from '@/utils/date'
import { resolveFieldError } from '@/utils/errors'
import { formatMoney, typeLabel } from '@/utils/format'

const month = ref(currentMonth())
const type = ref('')
const categoryId = ref('')

/** 已生效的搜索条件（点「查询」后才更新，避免输入过程频繁请求） */
const appliedSearch = reactive({ startDate: '', endDate: '', keyword: '' })

const rows = ref([])
const categories = ref([])
const loading = ref(false)
const error = ref('')

const formVisible = ref(false)
const editingRecord = ref(null)

const confirmVisible = ref(false)
const deleting = ref(false)
const deleteTarget = ref(null)

const categoryMap = computed(() => {
  const map = {}
  categories.value.forEach((item) => {
    map[item.id] = item.name
  })
  return map
})

const searchActive = computed(() =>
  Boolean(appliedSearch.startDate || appliedSearch.endDate || appliedSearch.keyword),
)
const hasFilter = computed(
  () => Boolean(type.value) || Boolean(categoryId.value) || searchActive.value,
)
const emptyText = computed(() =>
  hasFilter.value ? '没有符合条件的记录' : '本月暂无账单记录',
)
const emptyActionText = computed(() => {
  if (searchActive.value) return '清除搜索'
  if (hasFilter.value) return '重置筛选'
  return '＋ 记一笔'
})

const confirmMessage = computed(() => '确认删除该记录？')
const confirmDetail = computed(() => {
  const row = deleteTarget.value
  if (!row) return ''
  return `${row.date} · ${categoryMap.value[row.category_id] ?? '—'} · ${formatMoney(row.amount)}`
})

async function loadCategories() {
  try {
    categories.value = await listCategories()
  } catch (err) {
    ElMessage.error(err?.message || '分类加载失败')
  }
}

async function loadRows() {
  loading.value = true
  error.value = ''
  try {
    const params = {
      type: type.value || undefined,
      categoryId: categoryId.value || undefined,
    }
    if (searchActive.value) {
      params.startDate = appliedSearch.startDate || undefined
      params.endDate = appliedSearch.endDate || undefined
      params.keyword = appliedSearch.keyword || undefined
    } else {
      params.month = month.value
    }
    rows.value = await listTransactions(params)
  } catch (err) {
    error.value = err?.message || '加载失败'
    rows.value = []
  } finally {
    loading.value = false
  }
}

watch([month, type, categoryId], loadRows)

function applySearch({ startDate, endDate, keyword }) {
  if (startDate && endDate && startDate > endDate) {
    ElMessage.warning('开始日期不能晚于结束日期')
    return
  }
  appliedSearch.startDate = startDate
  appliedSearch.endDate = endDate
  appliedSearch.keyword = keyword
  loadRows()
}

function resetSearchState() {
  appliedSearch.startDate = ''
  appliedSearch.endDate = ''
  appliedSearch.keyword = ''
}

function clearSearch() {
  resetSearchState()
  loadRows()
}

function resetFilter() {
  const monthChanged = month.value !== currentMonth()
  month.value = currentMonth()
  type.value = ''
  categoryId.value = ''
  resetSearchState()
  // 月份未变化时 watch 不会触发，需手动刷新；变化时由 watch 负责
  if (!monthChanged) loadRows()
}

function exportCsv() {
  if (!rows.value.length) {
    ElMessage.warning('当前没有可导出的记录')
    return
  }
  const data = rows.value.map((row) => [
    row.date,
    typeLabel(row.type),
    categoryMap.value[row.category_id] ?? '',
    Number(row.amount).toFixed(2),
    row.note || '',
  ])
  const content = toCsv(['日期', '类型', '分类', '金额(元)', '备注'], data)
  downloadCsv(`账单_${today()}.csv`, content)
  ElMessage.success(`已导出 ${rows.value.length} 条记录`)
}

function openCreate() {
  editingRecord.value = null
  formVisible.value = true
}

function openEdit(row) {
  editingRecord.value = row
  formVisible.value = true
}

function onEmptyAction() {
  if (searchActive.value) clearSearch()
  else if (hasFilter.value) resetFilter()
  else openCreate()
}

function askDelete(row) {
  deleteTarget.value = row
  confirmVisible.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await deleteTransaction(deleteTarget.value.id)
    ElMessage.success('删除成功')
    confirmVisible.value = false
    await loadRows()
  } catch (err) {
    const result = resolveFieldError(err)
    ElMessage.warning(result.message)
    confirmVisible.value = false
    // 1008 记录不存在：刷新列表（数据可能已被删除，front-ui §3.6）
    if (result.refresh) await loadRows()
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadCategories()
  loadRows()
})
</script>