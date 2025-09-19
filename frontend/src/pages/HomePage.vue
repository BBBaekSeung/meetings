<!-- src/pages/HomePage.vue (핵심만) -->
<template>
  <div class="max-w-5xl mx-auto p-6">
    <h1 class="text-2xl font-semibold mb-6">스마트 회의록</h1>

    <!-- ✅ 호버 사이드바 고정 -->
    <HoverSidebar />

    <!-- 메인 컨텐츠: 사이드바는 겹쳐서 뜨므로 별도 그리드 필요 X -->
    <main class="space-y-6">
      <div class="flex items-center gap-3">
        <label class="text-sm text-gray-600">회의 이름:</label>
        <input
          v-model="meetingName"
          class="border rounded-lg px-3 py-1.5 flex-1"
          placeholder="회의 이름을 입력하세요 (기본: 나의 회의)"
        />
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <UploadCard :meetingName="meetingName" />
        <MobileStartCard :meetingName="meetingName" />
      </div>
    </main>
  </div>
</template>



<script setup lang="ts">
import { ref } from 'vue'
import UploadCard from '../components/UploadCard.vue'
import MobileStartCard from '../components/MobileStartCard.vue'
import HoverSidebar from '../components/HoverSidebar.vue'

const meetingName = ref('')
</script>
