<template>
  <section class="page">
    <div class="page__bar">
      <h2 class="page__title">分类管理</h2>
      <el-button type="primary" @click="formVisible = true">＋ 新增分类</el-button>
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

    <div v-loading="loading" class="page__body">
      <template v-if="!error">
        <CategoryGroupList
          v-if="categories.length"
          :categories="categories"
          @delete="askDelete"
        />
        <EmptyState v-else-if="!loading" text="暂无分类">
          <el-button type="primary" @click="formVisible = true">＋ 新增分类</el-button>
        </EmptyState>
      </template>
    </div>

    <CategoryFormDialog v-model="formVisible" @success="load" />

    <ConfirmDialog
      v-model="confirmVisible"
      :message="confirmMessage"
      :error="deleteError"
      :loading="deleting"
      @confirm="confirmDelete"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { deleteCategory, listCategories } from '@/api/categories'
import CategoryFormDialog from '@/components/CategoryFormDialog.vue'
import CategoryGroupList from '@/components/CategoryGroupList.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import { resolveFieldError } from '@/utils/errors'

const categories = ref([])
const loading = ref(false)
const error = ref('')

const formVisible = ref(false)
const confirmVisible = ref(false)
const deleting = ref(false)
const deleteTarget = ref(null)
const deleteError = ref('')

const confirmMessage = computed(() =>
  deleteTarget.value ? `确认删除分类「${deleteTarget.value.name}」？` : '',
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    categories.value = await listCategories()
  } catch (err) {
    error.value = err?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function askDelete(category) {
  deleteTarget.value = category
  deleteError.value = ''
  confirmVisible.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await deleteCategory(deleteTarget.value.id)
    ElMessage.success('删除成功')
    confirmVisible.value = false
    await load()
  } catch (err) {
    const { message } = resolveFieldError(err)
    if (err?.code === 1010) {
      // 被账单引用：确认框保持打开并就地显示后端错误（front-ui §1.3）
      deleteError.value = message
    } else {
      // 1007 分类不存在：关闭确认框、提示并刷新分组（front-ui §1.3、§4.4）
      ElMessage.warning(message)
      confirmVisible.value = false
      if (err?.code === 1007) await load()
    }
  } finally {
    deleting.value = false
  }
}

onMounted(load)
</script>