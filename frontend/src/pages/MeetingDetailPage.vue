<script setup lang="ts">
import { ref, watch } from 'vue'              // ✅ watch 추가
import { useRoute } from 'vue-router'
import { useMeeting } from '../composables/useMeeting'
import { updateMeetingName } from '../lib/api'
import ProgressBar from '../components/ProgressBar.vue'
import SummaryPanel from '../components/SummaryPanel.vue'
import TasksPanel from '../components/TasksPanel.vue'

const route = useRoute()
const meetingId = String(route.params.id || '')

// ✅ refetch 함께 구조분해
const { data: meeting, refetch } = useMeeting(meetingId)

const BASE = '스마트 회의록'
watch(() => meeting.value?.name, (name) => {
  document.title = name ? `${name} | ${BASE}` : `회의 상세 | ${BASE}`
}, { immediate: true })

// 인라인 편집 상태
const editing = ref(false)
const draftName = ref('')

function startEdit() {
  draftName.value = meeting.value?.name || ''   // ✅ data → meeting
  editing.value = true
}

async function saveEdit() {
  if (draftName.value.trim() && meeting.value) {
    await updateMeetingName(meeting.value.id, draftName.value.trim()) // ✅ data → meeting
    await refetch()
  }
  editing.value = false
}

function cancelEdit() {
  editing.value = false
}

const onRefresh = () => { void refetch() }
</script>

<template>
  <!-- ✅ v-if도 meeting으로 -->
  <div class="max-w-5xl mx-auto p-6 space-y-6" v-if="meeting">
    <div class="flex items-center gap-3">
      <div @dblclick="startEdit" class="flex items-center gap-2">
        <template v-if="editing">
        <input
          v-model="draftName"
          class="border rounded px-2 py-1 text-lg font-semibold"
          @keyup.enter="saveEdit"
          @blur="cancelEdit"
        />
        <button class="px-2 py-1 rounded border" type="button" @mousedown.prevent="saveEdit">저장</button>

        </template>
        <template v-else>
          <h1 class="text-2xl font-semibold cursor-pointer">
            {{ meeting?.name }}   <!-- ✅ data → meeting -->
          </h1>
        </template>
      </div>

      <span class="text-sm px-2 py-1 rounded-full border">{{ meeting?.status }}</span>
           <div class="ml-auto flex items-center gap-2">
       <RouterLink
         to="/"
         class="px-3 py-1 rounded-xl border hover:bg-gray-50 transition"
         aria-label="홈으로 이동">
         홈
       </RouterLink>
       <button class="px-3 py-1 rounded-xl border" @click="onRefresh">새로고침</button>
     </div>
    </div>

    <ProgressBar :value="meeting?.progress || 0" />

    <div v-if="meeting?.status !== 'completed'" class="text-sm text-gray-600">
      처리 중입니다. 완료되면 요약과 할 일이 표시됩니다.
    </div>
    <div v-else-if="meeting?.result?.error" class="text-red-600">
      처리에 실패했습니다: {{ meeting?.result?.error }}
    </div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="p-4 rounded-2xl border">
        <h2 class="text-lg font-semibold mb-3">요약(3문단)</h2>
        <SummaryPanel :summary="meeting?.result?.summary" />
      </div>
      <div class="p-4 rounded-2xl border">
        <h2 class="text-lg font-semibold mb-3">업무(Task)</h2>
        <TasksPanel :actions="meeting?.result?.actions" />
      </div>
    </div>
  </div>
  <div v-else class="p-6">불러오는 중...</div>
</template>
