<template>
  <section class="page">
    <div class="page__bar">
      <h2 class="page__title">数据看板</h2>
      <MonthSwitcher v-model="month" />
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      class="page__alert"
    >
      <template #default>
        <el-button link type="primary" @click="load">重试</el-button>
      </template>
    </el-alert>

    <div class="budget-bar">
      <div class="budget-bar__info">
        <span class="budget-bar__label">本月预算</span>
        <span v-if="budget.amount === null" class="budget-bar__empty">未设置</span>
        <span v-else class="budget-bar__amount">{{ formatMoney(budget.amount) }}</span>
        <span v-if="budget.amount !== null" class="budget-bar__usage">
          已支出 {{ formatMoney(report.total_expense) }} · {{ budgetUsageText }}
        </span>
      </div>
      <el-progress
        v-if="budget.amount !== null"
        :percentage="budgetProgress"
        :status="overBudget ? 'exception' : undefined"
        :stroke-width="10"
        class="budget-bar__progress"
      />
      <el-button size="small" @click="openBudgetDialog">
        {{ budget.amount === null ? '设置预算' : '修改预算' }}
      </el-button>
    </div>

    <div v-loading="loading" class="dashboard">
      <div class="stat-row">
        <StatCard title="本月收入" :amount="report.total_income" tone="income" />
        <StatCard title="本月支出" :amount="report.total_expense" tone="expense" />
        <StatCard title="本月结余" :amount="report.balance" tone="balance" />
      </div>

      <h3 class="section-title">支出分类占比</h3>
      <div class="pie-row">
        <div class="pie-row__chart">
          <ExpensePieChart :items="expenseItems" :empty-text="pieEmptyText" />
        </div>
        <div class="pie-row__list">
          <CategoryBreakdownList v-if="expenseItems.length" :items="expenseItems" />
          <EmptyState v-else :text="pieEmptyText" />
        </div>
      </div>
    </div>

    <el-dialog
      v-model="budgetDialogVisible"
      title="设置月度预算"
      width="420px"
      :close-on-click-modal="false"
    >
      <el-form label-width="90px" @submit.prevent>
        <el-form-item label="月份">
          <el-input :model-value="month" disabled />
        </el-form-item>
        <el-form-item label="预算金额" :error="budgetError">
          <el-input-number
            v-model="budgetInput"
            :min="0.01"
            :max="99999999.99"
            :precision="2"
            :step="100"
            :controls="false"
            placeholder="请输入预算金额"
            style="width: 100%"
            @input="budgetError = ''"
          />
          <span class="form-hint">元（必须大于 0，最多 2 位小数）</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="budgetSaving" @click="budgetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="budgetSaving" @click="saveBudget">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { getBudget, setBudget } from '@/api/budgets'
import { getMonthlyReport } from '@/api/reports'
import CategoryBreakdownList from '@/components/CategoryBreakdownList.vue'
import EmptyState from '@/components/EmptyState.vue'
import ExpensePieChart from '@/components/ExpensePieChart.vue'
import MonthSwitcher from '@/components/MonthSwitcher.vue'
import StatCard from '@/components/StatCard.vue'
import { currentMonth } from '@/utils/date'
import { formatMoney } from '@/utils/format'

const month = ref(currentMonth())
const loading = ref(false)
const error = ref('')
const report = reactive({
  total_income: 0,
  total_expense: 0,
  balance: 0,
  expense_by_category: [],
})

/** 月度预算（选做功能 1）；amount=null 表示未设置 */
const budget = reactive({ amount: null })
const budgetDialogVisible = ref(false)
const budgetInput = ref(null)
const budgetError = ref('')
const budgetSaving = ref(false)
/** 已弹过超支提醒的月份，避免同月重复弹窗 */
const warnedMonth = ref('')

const expenseItems = computed(() => report.expense_by_category || [])

const overBudget = computed(
  () => budget.amount !== null && report.total_expense > Number(budget.amount),
)

const budgetProgress = computed(() => {
  if (budget.amount === null || Number(budget.amount) <= 0) return 0
  return Math.min(100, Number(((report.total_expense / Number(budget.amount)) * 100).toFixed(1)))
})

const budgetUsageText = computed(() => {
  if (budget.amount === null || Number(budget.amount) <= 0) return ''
  const percent = ((report.total_expense / Number(budget.amount)) * 100).toFixed(1)
  if (overBudget.value) {
    return `已超支 ${formatMoney(report.total_expense - Number(budget.amount))}（${percent}%）`
  }
  return `预算使用 ${percent}%`
})

/** 空状态文案（front-ui §2.4、api-design §3.8） */
const pieEmptyText = computed(() => {
  if (report.total_income === 0 && report.total_expense === 0) return '本月暂无数据'
  return '本月暂无支出数据'
})

function applyReport(data) {
  report.total_income = Number(data?.total_income ?? 0)
  report.total_expense = Number(data?.total_expense ?? 0)
  report.balance = Number(data?.balance ?? 0)
  report.expense_by_category = Array.isArray(data?.expense_by_category)
    ? data.expense_by_category
    : []
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    applyReport(await getMonthlyReport(month.value))
  } catch (err) {
    error.value = err?.message || '加载失败'
  } finally {
    loading.value = false
  }
  await loadBudget()
  checkOverBudget()
}

async function loadBudget() {
  try {
    const data = await getBudget(month.value)
    budget.amount = data?.amount === null || data?.amount === undefined ? null : Number(data.amount)
  } catch {
    // 预算加载失败不阻塞报表展示
    budget.amount = null
  }
}

function checkOverBudget() {
  if (!overBudget.value || warnedMonth.value === month.value) return
  warnedMonth.value = month.value
  ElMessageBox.alert(
    `本月支出 ${formatMoney(report.total_expense)}，已超过预算 ${formatMoney(budget.amount)}，超支 ${formatMoney(
      report.total_expense - Number(budget.amount),
    )}。`,
    '预算超支提醒',
    { type: 'warning', confirmButtonText: '知道了' },
  )
}

function openBudgetDialog() {
  budgetInput.value = budget.amount === null ? null : Number(budget.amount)
  budgetError.value = ''
  budgetDialogVisible.value = true
}

async function saveBudget() {
  const amount = Number(budgetInput.value)
  if (budgetInput.value === null || budgetInput.value === '' || Number.isNaN(amount) || amount <= 0) {
    budgetError.value = '预算金额不合法'
    return
  }
  if (amount > 99999999.99) {
    budgetError.value = '预算超出允许范围'
    return
  }
  budgetSaving.value = true
  budgetError.value = ''
  try {
    const data = await setBudget({ month: month.value, amount })
    budget.amount = data?.amount === null || data?.amount === undefined ? null : Number(data.amount)
    budgetDialogVisible.value = false
    ElMessage.success('预算已保存')
    checkOverBudget()
  } catch (err) {
    budgetError.value = err?.message || '保存失败'
  } finally {
    budgetSaving.value = false
  }
}

watch(month, load)
onMounted(load)
</script>

<style scoped>
.budget-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px 20px;
  background: #ffffff;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
}

.budget-bar__info {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 320px;
}

.budget-bar__label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.budget-bar__empty {
  color: var(--el-text-color-secondary);
  font-size: 16px;
}

.budget-bar__amount {
  font-size: 18px;
  font-weight: 600;
}

.budget-bar__usage {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.budget-bar__progress {
  flex: 1;
  max-width: 360px;
}

.form-hint {
  display: block;
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.4;
}
</style>