<!-- src/components/MeetingListSidebar.vue -->
<template>
  <!-- 상단 여백을 주어 전체를 조금 아래로 -->
  <aside class="md:sticky md:top-4 space-y-3 pt-5">
    <!-- 검색/리프레시 행도 추가로 아래로 -->
    <div class="mt-3 flex items-center gap-2">
      <input
        v-model="keyword"
        class="w-full border rounded-lg px-3 py-2.5"
        placeholder="회의 검색"
        @keyup.enter="refetch()"
      />

      <!-- 아이콘 버튼: 가운데 정렬 & baseline 보정 -->
      <button
        class="inline-flex items-center justify-center p-2.5 rounded-lg border hover:bg-gray-50 shadow-sm"
        title="새로고침"
        aria-label="새로고침"
        @click="refetch()"
      >
        <i class="fi fi-bs-refresh text-xl leading-none"></i>
      </button>
    </div>

    <div v-if="isLoading" class="text-sm text-gray-500">불러오는 중…</div>
    <div v-else-if="error" class="text-sm text-red-600">목록을 불러오지 못했습니다.</div>
    <div v-else-if="filtered.length === 0" class="text-sm text-gray-500">회의가 없습니다.</div>

    <nav v-else class="space-y-2">
      <RouterLink
        v-for="m in filtered"
        :key="m.id"
        :to="`/meetings/${m.id}`"
        class="block rounded-xl border p-3 hover:bg-gray-50 transition"
      >
        <div class="font-medium truncate" :title="m.name">{{ m.name }}</div>
        <div class="mt-1 text-xs text-gray-500">
          {{ formatDate(m.created_at || m.updated_at) }}
        </div>
      </RouterLink>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useMeetings } from '../composables/useMeeting'

const keyword = ref('')
const { data, isLoading, error, refetch } = useMeetings({ order: 'desc', limit: 50 })

const filtered = computed(() => {
  const list = data?.value || []
  const q = keyword.value.trim().toLowerCase()
  if (!q) return list
  return list.filter(m => (m.name || '').toLowerCase().includes(q) || (m.id || '').toLowerCase().includes(q))
})

function formatDate(s?: string) {
  if (!s) return ''
  try { 
    return new Date(s).toLocaleString('ko-KR')
  } catch { 
    return s 
  }
}
</script>
