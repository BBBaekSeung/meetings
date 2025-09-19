<script setup lang="ts">
import { ref } from 'vue'
import TaskDetailDrawer from './TaskDetailDrawer.vue'

type T = Record<string, any>
const props = defineProps<{ actions?: T[], meetingId?: string }>()
const open = ref(false)
const selected = ref<T | null>(null)

// 상태 뱃지 색상만 상태값(value) 기준으로 매핑
const STATUS_CLASS: Record<string, string> = {
  todo: 'bg-gray-200 text-gray-700',
  in_progress: 'bg-orange-200 text-orange-900',
  feedback: 'bg-indigo-200 text-indigo-900',
  on_hold: 'bg-amber-100 text-amber-800',
  canceled: 'bg-red-100 text-red-700 line-through',
  done: 'bg-green-100 text-green-800',
}

// 날짜 포맷
function ymd(dateLike: any) {
  if (!dateLike) return '—'
  const d = typeof dateLike === 'string' ? new Date(dateLike) : dateLike
  if (isNaN(d as any)) return '—'
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}.${mm}.${dd}`
}

// 담당자 전체 표시 (배열/문자열 모두 흡수)
function allAssignees(a: T): string[] {
  const v = a.assignees_json ?? a.assignees ?? []
  if (Array.isArray(v)) return v.filter(Boolean)
  if (typeof v === 'string' && v.trim()) return [v.trim()]
  return []
}

function openDetail(a: T) {
  selected.value = {
    ...a,
    // enum 객체/문자열 모두 대응
    status: a.status?.value ?? a.status,
    task_type: a.task_type?.value ?? a.task_type,
    assignees_json: a.assignees_json ?? a.assignees ?? [],
  }
  open.value = true
}

function onSaved(updated: T) {
  if (!props.actions) return
  const idx = props.actions.findIndex(x => x.id === updated.id)
  if (idx >= 0) props.actions[idx] = { ...props.actions[idx], ...updated }
}
</script>

<template>
  <div v-if="!actions || actions.length === 0" class="text-sm text-gray-500">
    할 일이 추출되지 않았습니다.
  </div>

  <div v-else class="space-y-3">
    <button
      v-for="a in actions" :key="a.id ?? a.title"
      class="w-full text-left p-4 rounded-xl border hover:bg-gray-50 transition"
      @click="openDetail(a)"
    >
      <!-- 제목 -->
      <div class="font-medium line-clamp-1 text-base">
        {{ a.title }}
      </div>

      <!-- 상태(라벨은 서버 제공) + 시작일자 -->
      <div class="flex items-center gap-2 mt-2 text-xs">
        <span
          class="inline-flex items-center px-2 py-0.5 rounded-full font-medium"
          :class="STATUS_CLASS[a.status?.value ?? a.status ?? 'todo']"
        >
          {{ a.status_label || (a.status?.value ?? a.status ?? '').toString() }}
        </span>
        <span class="text-gray-500">시작 {{ ymd(a.start_date) }}</span>
      </div>

      <!-- 담당자: 전원 풀네임 표시 (자동 줄바꿈) -->
      <div class="flex flex-wrap gap-1 mt-3">
        <span
          v-for="n in allAssignees(a)"
          :key="n"
          class="px-2 py-1 rounded-full border bg-white text-xs"
        >
          {{ n }}
        </span>
        <span v-if="allAssignees(a).length === 0" class="text-xs text-gray-400">—</span>
      </div>
    </button>
  </div>

  <TaskDetailDrawer
    v-model="open"
    :task="selected"
    :meetingId="meetingId || ''"
    @saved="onSaved"
  />
</template>
