<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useMeeting } from '../composables/useMeeting'
import { updateMeetingName } from '../lib/api'
import ProgressBar from '../components/ProgressBar.vue'
import SummaryPanel from '../components/SummaryPanel.vue'
import TasksPanel from '../components/TasksPanel.vue'
import FullscriptPanel from '../components/FullscriptPanel.vue'
import TranscriptBubbles from '../components/TranscriptBubbles.vue'

type LeftTab = 'summary' | 'fullscript'
const leftTab = ref<LeftTab>('summary')

const route = useRoute()
const meetingId = String(route.params.id || '')
const { data: meeting, refetch } = useMeeting(meetingId)

// 결과 완료일 때만 fullscript 호출
const fullscriptEnabled = computed(() => meeting.value?.status === 'completed')

const BASE = '스마트 회의록'
watch(
  () => meeting.value?.name,
  (name) => {
    document.title = name ? `${name} | ${BASE}` : `회의 상세 | ${BASE}`
  },
  { immediate: true }
)

// 인라인 편집 상태
const editing = ref(false)
const draftName = ref('')

function startEdit() {
  draftName.value = meeting.value?.name || ''
  editing.value = true
}

async function saveEdit() {
  if (draftName.value.trim() && meeting.value) {
    await updateMeetingName(meeting.value.id, draftName.value.trim())
    await refetch()
  }
  editing.value = false
}

function cancelEdit() {
  editing.value = false
}

const onRefresh = () => {
  void refetch()
}
</script>

<template>
  <!-- ✅ 최상위에서 meeting 유무 분기 (template 블록으로 감싸 주석/공백 간섭 방지) -->
  <template v-if="meeting">
    <div class="max-w-5xl mx-auto p-6 space-y-6">
      <!-- 헤더 -->
      <div class="flex items-center gap-3">
        <div @dblclick="startEdit" class="flex items-center gap-2">
          <template v-if="editing">
            <input
              v-model="draftName"
              class="border rounded px-2 py-1 text-lg font-semibold"
              @keyup.enter="saveEdit"
              @blur="cancelEdit"
            />
            <button
              class="px-2 py-1 rounded border"
              type="button"
              @mousedown.prevent="saveEdit"
            >
              저장
            </button>
          </template>
          <template v-else>
            <h1 class="text-2xl font-semibold cursor-pointer">
              {{ meeting?.name }}
            </h1>
          </template>
        </div>

        <span class="text-sm px-2 py-1 rounded-full border">
          {{ meeting?.status }}
        </span>

        <div class="ml-auto flex items-center gap-2">
          <RouterLink
            to="/"
            class="px-3 py-1 rounded-xl border hover:bg-gray-50 transition"
            aria-label="홈으로 이동"
          >
            홈
          </RouterLink>
          <button class="px-3 py-1 rounded-xl border" @click="onRefresh">
            새로고침
          </button>
        </div>
      </div>

      <ProgressBar :value="meeting?.progress || 0" />

      <!-- 내부 상태 분기 -->
      <div v-if="meeting?.status !== 'completed'" class="text-sm text-gray-600">
        처리 중입니다. 완료되면 요약과 할 일이 표시됩니다.
      </div>
      <div v-else-if="meeting?.result?.error" class="text-red-600">
        처리에 실패했습니다: {{ meeting?.result?.error }}
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
<!-- ✅ 왼쪽 카드 (탭 전환: 요약 ↔ 전체 스크립트) -->
<div class="relative overflow-visible"> <!-- overflow-visible 중요 -->
  <!-- 탭: 카드 왼쪽 바깥으로 완전히 빼기 -->
  <nav
    class="hidden md:flex flex-col gap-1 absolute left-0 top-3 -translate-x-full z-10"
    aria-label="회의 결과 탭"
  >
    <button
      class="px-3 py-1 text-sm rounded border transition
             aria-selected:bg-gray-900 aria-selected:text-white
             not-aria-selected:bg-gray-100 not-aria-selected:text-gray-700
             hover:not-aria-selected:bg-gray-200"
      :aria-selected="leftTab === 'summary'"
      @click="leftTab = 'summary'"
    >
      요약
    </button>
    <button
      class="px-3 py-1 text-sm rounded border transition
             aria-selected:bg-gray-900 aria-selected:text-white
             not-aria-selected:bg-gray-100 not-aria-selected:text-gray-700
             hover:not-aria-selected:bg-gray-200"
      :aria-selected="leftTab === 'fullscript'"
      @click="leftTab = 'fullscript'"
    >
      스크립트
    </button>
  </nav>

  <!-- 카드: 그대로 전체 너비 사용 -->
  <div class="p-4 rounded-2xl border bg-white h-full">
    <h2 class="text-lg font-semibold mb-3">
      {{ leftTab === 'summary' ? '요약(3문단)' : '전체 스크립트' }}
    </h2>

    <div v-if="leftTab === 'summary'">
      <SummaryPanel :summary="meeting?.result?.summary" />
    </div>
    <div v-else>
      <TranscriptBubbles
        :meeting-id="String(meeting?.id || '')"
        :enabled="fullscriptEnabled"
      />
    </div>
  </div>
</div>


        <!-- ✅ 오른쪽 카드 -->
        <div class="p-4 rounded-2xl border h-full">
          <h2 class="text-lg font-semibold mb-3">업무(Task)</h2>
        <!-- ✅ 저장 이벤트를 받아서 refetch -->
        <TasksPanel
          :actions="meeting?.result?.actions"
          :meetingId="meeting?.id"
          @saved="refetch()"
        />
        </div>
      </div>
    </div>
  </template>

  <template v-else>
    <div class="max-w-5xl mx-auto p-6">불러오는 중...</div>
  </template>
</template>
