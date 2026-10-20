import { createRouter, createWebHistory } from 'vue-router'

import { getToken } from '../api/http'

const routes = [
  { path: '/', redirect: '/rooms' },
  { path: '/login', name: 'login', component: () => import('../pages/Login.vue'), meta: { public: true } },
  { path: '/rooms', name: 'rooms', component: () => import('../pages/RoomList.vue') },
  { path: '/rooms/:id', name: 'room-detail', component: () => import('../pages/RoomDetail.vue') },
  { path: '/records', name: 'records', component: () => import('../pages/Records.vue') },
  { path: '/ranking', name: 'ranking', component: () => import('../pages/Ranking.vue') },
  { path: '/agent', name: 'agent', component: () => import('../pages/Agent.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/rooms' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  // 配合"向下滚动切换"，换页后回到顶部，否则下一个页面会停在中间
  scrollBehavior: () => ({ top: 0, left: 0 }),
})

router.beforeEach((to) => {
  if (to.meta.public) return true
  if (!getToken()) return { name: 'login', query: { redirect: to.fullPath } }
  return true
})

export default router