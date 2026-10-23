<template>
  <div class="category-groups">
    <div v-for="group in groups" :key="group.type" class="category-group">
      <div class="category-group__header">
        ── {{ group.label }} ({{ group.items.length }}) ──
      </div>
      <ul v-if="group.items.length" class="category-group__list">
        <li v-for="item in group.items" :key="item.id" class="category-group__item">
          <span class="category-group__name">{{ item.name }}</span>
          <el-button link type="danger" @click="emit('delete', item)">删除</el-button>
        </li>
      </ul>
      <el-empty v-else :description="group.emptyText" :image-size="48" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 全部分类（接口顺序：type 升序 → expense 组在前、income 组在后） */
  categories: { type: Array, default: () => [] },
})
const emit = defineEmits(['delete'])

const groups = computed(() => [
  {
    type: 'expense',
    label: '支出分类',
    emptyText: '暂无支出分类',
    items: props.categories.filter((item) => item.type === 'expense'),
  },
  {
    type: 'income',
    label: '收入分类',
    emptyText: '暂无收入分类',
    items: props.categories.filter((item) => item.type === 'income'),
  },
])
</script>

<style scoped>
.category-group {
  margin-bottom: 20px;
}

.category-group__header {
  margin-bottom: 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.category-group__list {
  margin: 0;
  padding: 0;
  list-style: none;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
}

.category-group__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
}

.category-group__item + .category-group__item {
  border-top: 1px solid var(--el-border-color-lighter);
}

.category-group__name {
  font-size: 14px;
}
</style>