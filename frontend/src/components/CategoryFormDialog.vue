<template>
  <el-dialog
    :model-value="modelValue"
    title="新增分类"
    width="460px"
    :close-on-click-modal="false"
    @update:model-value="onVisibleChange"
  >
    <el-form label-width="80px" @submit.prevent>
      <el-form-item label="类型" required>
        <el-radio-group v-model="form.type">
          <el-radio value="expense">支出</el-radio>
          <el-radio value="income">收入</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="名称" required :error="nameError">
        <el-input
          v-model="form.name"
          maxlength="20"
          show-word-limit
          placeholder="请输入分类名称"
          @input="nameError = ''"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button :disabled="loading" @click="close">取消</el-button>
      <el-button type="primary" :loading="loading" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { createCategory } from '@/api/categories'
import { codePointLength } from '@/utils/date'
import { resolveFieldError } from '@/utils/errors'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'success'])

const loading = ref(false)
const nameError = ref('')
const form = reactive({ type: 'expense', name: '' })

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) return
    // 每次打开重置（默认类型"支出"，front-ui §4.3）
    form.type = 'expense'
    form.name = ''
    nameError.value = ''
  },
)

function close() {
  emit('update:modelValue', false)
}

function onVisibleChange(visible) {
  if (!visible && loading.value) return
  emit('update:modelValue', visible)
}

async function submit() {
  const name = form.name.trim()
  const len = codePointLength(name)
  // 前端即时校验：去首尾空格后 1–20 个 Unicode 码点（spec §5.2、E-10）
  if (len < 1 || len > 20) {
    nameError.value = '分类名称不合法'
    return
  }
  nameError.value = ''
  loading.value = true
  try {
    await createCategory({ name, type: form.type })
    ElMessage.success('新增成功')
    emit('success')
    close()
  } catch (err) {
    const { field, message } = resolveFieldError(err)
    if (field === 'name') nameError.value = message
    else ElMessage.error(message)
  } finally {
    loading.value = false
  }
}
</script>