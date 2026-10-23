import { createRouter, createWebHistory } from 'vue-router'

// 路由归属已定稿（spec.md §6.4 v1.3、front-ui.md §0）
// `/` = 首页数据看板；`/transactions` = 账单管理；`/categories` = 分类管理
const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: '数据看板' },
  },
  {
    path: '/transactions',
    name: 'transactions',
    component: () => import('@/views/TransactionsView.vue'),
    meta: { title: '账单管理' },
  },
  {
    path: '/categories',
    name: 'categories',
    component: () => import('@/views/CategoriesView.vue'),
    meta: { title: '分类管理' },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} · 个人记账本` : '个人记账本'
})

export default router