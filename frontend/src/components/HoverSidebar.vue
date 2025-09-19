<!-- src/components/HoverSidebar.vue -->
<template>
  <!-- 전체 wrapper -->
  <div class="fixed inset-y-0 left-0 z-40 flex">
    <!-- 토글 버튼 (항상 보이는 아이콘) -->
    <button
      class="m-2 p-2 bg-gray-300 hover:bg-gray-400 rounded-md shadow cursor-pointer"
      title="회의 목록"
      @click="isOpen = !isOpen"
    >
      <!-- 예: 햄버거 아이콘 -->
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>

    <!-- 사이드바 패널 -->
    <transition name="slide">
      <aside
        v-if="isOpen"
        class="h-full w-[280px] bg-white border-r shadow-sm p-3 overflow-y-auto"
      >
        <MeetingListSidebar />
      </aside>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import MeetingListSidebar from '../components/MeetingListSidebar.vue'

const isOpen = ref(false)
</script>

<style>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.2s ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(-100%);
}
</style>
