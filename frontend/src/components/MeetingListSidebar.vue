<!-- src/components/MeetingListSidebar.vue (간단 버전) -->
<template>
  <aside class="md:sticky md:top-4 space-y-3">
    <div class="flex items-center gap-2">
      <input
        v-model="keyword"
        class="w-full border rounded-lg px-3 py-1.5"
        placeholder="회의 검색"
        @keyup.enter="refetch()"
      />
      <button class="px-3 py-1 rounded-lg border" @click="refetch()">새로고침</button>
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
    // 백엔드가 +09:00로 내려주면 이거면 충분
    return new Date(s).toLocaleString('ko-KR')
  } catch { 
    return s 
  }
}
</script>
