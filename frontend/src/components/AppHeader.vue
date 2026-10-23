<template>
  <header class="app-header">
    <div class="app-header__brand">个人记账本</div>
    <el-menu
      class="app-header__menu"
      mode="horizontal"
      router
      :default-active="activePath"
      :ellipsis="false"
    >
      <el-menu-item index="/">数据看板</el-menu-item>
      <el-menu-item index="/transactions">账单管理</el-menu-item>
      <el-menu-item index="/categories">分类管理</el-menu-item>
    </el-menu>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activePath = computed(() => route.path)
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 0 24px;
  height: 56px;
  background: #ffffff;
  border-bottom: 1px solid var(--el-border-color-light);
}

.app-header__brand {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;
}

.app-header__menu {
  flex: 1;
  border-bottom: none;
}
</style>