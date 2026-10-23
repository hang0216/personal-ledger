<template>
  <el-dialog
    :model-value="modelValue"
    :title="isEdit ? '编辑账单' : '新增账单'"
    width="520px"
    :close-on-click-modal="false"
    @update:model-value="onVisibleChange"
  >
    <el-form label-width="72px" @submit.prevent>
      <el-form-item label="类型" required>
        <el-radio-group v-model="form.type" @change="onTypeChange">
          <el-radio value="expense">支出</el-radio>
          <el-radio value="income">收入</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="金额" required :error="errors.amount">
        <el-input-number
          v-model="form.amount"
          :min="0"
          :max="99999999.99"
          :precision="2"
          :step="1"
          :controls="false"
          placeholder="请输入金额"
          style="width: 100%"
          @input="errors.amount = ''"
        />
        <span class="form-hint">元（必须大于 0，最多 2 位小数）</span>
      </el-form-item>

      <el-form-item label="分类" required :error="errors.category_id">
        <el-select
          v-model="form.category_id"
          placeholder="请选择分类"
          style="width: 100%"
          @change="errors.category_id = ''"
        >
          <el-option
            v-for="item in categoryOptions"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="日期" required :error="errors.date">
        <el-date-picker
          v-model="form.date"
          type="date"
          value-format="YYYY-MM-DD"
          format="YYYY-MM-DD"
          placeholder="选择日期"
          :disabled-date="disabledDate"
          style="width: 100%"
          @change="errors.date = ''"
        />
      </el-form-item>

      <el-form-item label="备注" :error="errors.note">
        <el-input
          v-model="form.note"
          placeholder="选填，最多 100 字"
          @input="onNoteInput"
        />
        <span class="form-hint">{{ noteLength }} / 100</span>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button :disabled="loading" @click="close">取消</el-button>
      <el-button type="primary" :loading="loading" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { createTransaction, updateTransaction } from '@/api/transactions'
import { MIN_DATE, codePointLength, isDateOutOfRange, today } from '@/utils/date'
import { resolveFieldError } from '@/utils/errors'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  /** 全部分类（用于按类型联动过滤下拉，front-ui §1.1） */
  categories: { type: Array, default: () => [] },
  /** 编辑时传入该行记录；新增时为 null */
  record: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'success', 'refresh-categories'])

const loading = ref(false)
const form = reactive({ type: 'expense', amount: null, category_id: null, date: '', note: '' })
const errors = reactive({ amount: '', category_id: '', date: '', note: '' })

const isEdit = computed(() => Boolean(props.record))
const noteLength = computed(() => codePointLength(form.note))
const categoryOptions = computed(() =>
  props.categories.filter((item) => item.type === form.type),
)

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) return
    reset()
  },
)

function reset() {
  errors.amount = ''
  errors.category_id = ''
  errors.date = ''
  errors.note = ''
  const record = props.record
  if (record) {
    form.type = record.type
    form.amount = Number(record.amount)
    form.category_id = record.category_id
    form.date = record.date
    form.note = record.note || ''
  } else {
    form.type = 'expense'
    form.amount = null
    form.category_id = null
    form.date = today()
    form.note = ''
  }
}

/** 切换收支类型后重新加载分类下拉并清空已选分类（front-ui §1.1） */
function onTypeChange() {
  form.category_id = null
  errors.category_id = ''
}

function disabledDate(date) {
  const text = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(
    date.getDate(),
  ).padStart(2, '0')}`
  return text < MIN_DATE || text > today()
}

/** 备注按 Unicode 码点限制 100（spec R-06），超出禁止输入 */
function onNoteInput(value) {
  const chars = [...value]
  if (chars.length > 100) form.note = chars.slice(0, 100).join('')
  errors.note = ''
}

function close() {
  emit('update:modelValue', false)
}

function onVisibleChange(visible) {
  if (!visible && loading.value) return
  emit('update:modelValue', visible)
}

function validate() {
  errors.amount = ''
  errors.category_id = ''
  errors.date = ''
  errors.note = ''
  const amount = Number(form.amount)
  if (form.amount === null || form.amount === '' || Number.isNaN(amount) || amount <= 0) {
    errors.amount = '金额不合法'
    return false
  }
  if (amount > 99999999.99) {
    errors.amount = '金额超出允许范围'
    return false
  }
  if (!form.category_id) {
    errors.category_id = '请选择分类'
    return false
  }
  if (!form.date || isDateOutOfRange(form.date)) {
    errors.date = '日期不合法'
    return false
  }
  if (codePointLength(form.note) > 100) {
    errors.note = '备注长度超限'
    return false
  }
  return true
}

async function submit() {
  if (!validate()) return
  const payload = {
    amount: Number(form.amount),
    type: form.type,
    category_id: form.category_id,
    date: form.date,
    note: form.note ? form.note : null,
  }
  loading.value = true
  try {
    if (isEdit.value) await updateTransaction(props.record.id, payload)
    else await createTransaction(payload)
    ElMessage.success('保存成功')
    emit('success')
    close()
  } catch (err) {
    const result = resolveFieldError(err)
    if (result.field && result.field in errors) {
      errors[result.field] = result.message
    } else {
      ElMessage.error(result.message)
    }
    // 1007 分类不存在：刷新分类列表并重置分类选择（front-ui §1.3）
    if (err?.code === 1007) {
      form.category_id = null
      emit('refresh-categories')
    }
    // 1008 记录不存在：关闭弹窗并刷新列表（front-ui §1.3）
    if (result.close) {
      close()
      emit('success')
    } else if (result.refresh) {
      emit('success')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.form-hint {
  display: block;
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.4;
}
</style>