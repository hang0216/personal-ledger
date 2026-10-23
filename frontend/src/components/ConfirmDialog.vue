<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    width="420px"
    :close-on-click-modal="false"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <div class="confirm-dialog__message">{{ message }}</div>
    <div v-if="detail" class="confirm-dialog__detail">{{ detail }}</div>
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      class="confirm-dialog__error"
    />
    <template #footer>
      <el-button :disabled="loading" @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="danger" :loading="loading" @click="emit('confirm')">确定删除</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '提示' },
  message: { type: String, default: '' },
  detail: { type: String, default: '' },
  /** 删除失败时的后端错误信息（如 1010），显示在确认框内且不自动关闭 */
  error: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'confirm'])
</script>

<style scoped>
.confirm-dialog__message {
  font-size: 14px;
}

.confirm-dialog__detail {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.confirm-dialog__error {
  margin-top: 12px;
}
</style>