<!-- src/components/HoverSidebar.vue -->
<template>
  <!-- 토글 버튼 (왼쪽 상단 고정) -->
  <button
    class="fixed top-2 left-2 z-50 p-2 bg-gray-300 hover:bg-gray-400 rounded-md shadow cursor-pointer flex items-center justify-center"
    @click="isOpen = !isOpen"
  >
  <i class="fi fi-bs-menu-dots text-2xl text-gray-700 leading-none"></i>
  </button>

  <!-- 사이드바 패널 -->
  <transition name="slide">
    <aside
      v-if="isOpen"
      class="fixed inset-y-0 left-0 z-40 w-[280px] bg-white border-r shadow-sm p-3 overflow-y-auto"
    >
      <MeetingListSidebar />
    </aside>
  </transition>
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
