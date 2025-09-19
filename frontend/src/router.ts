// src/router.ts
import { createRouter, createWebHistory } from 'vue-router'
import HomePage from './pages/HomePage.vue'
import MobileUploadPage from './pages/MobileUploadPage.vue'
import MeetingDetailPage from './pages/MeetingDetailPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomePage, meta: { title: '홈' } },
    { path: '/m/upload', component: MobileUploadPage, alias: ['/handoff/m/upload'], meta: { title: '모바일 업로드' } },
    // 동적 타이틀(회의명)은 페이지 내부에서 설정 (아래 3번)
    { path: '/meetings/:id', component: MeetingDetailPage, meta: { title: '회의 상세' } },
  ],
})

// 라우트 변경 시 기본 타이틀 세팅
const BASE = '스마트 회의록'
router.afterEach((to) => {
  const t = typeof to.meta.title === 'function' ? (to.meta.title as any)(to) : to.meta.title
  document.title = t ? `${t} | ${BASE}` : BASE
})

export default router