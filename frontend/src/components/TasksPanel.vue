<script setup lang="ts">
import { ref } from 'vue'
import { STATUS_LABEL, type TaskStatus, STATUS_BADGE_TW } from '../task.ts'
import TaskDetailDrawer from './TaskDetailDrawer.vue'

type T = Record<string, any>
const props = defineProps<{ actions?: T[], meetingId?: string }>()
const open = ref(false)
const selected = ref<T | null>(null)
const emit = defineEmits<{ (e: 'saved', payload: T): void }>()

const STATUS_CLASS = STATUS_BADGE_TW

// enum/문자열 모두 수용 + 기본값은 'in_progress'(진행)
function statusValue(s: any): TaskStatus {
  return (s?.value ?? s ?? 'in_progress') as TaskStatus
}

// 안전한 Date 파서
function toDate(dateLike: any): Date | null {
  if (!dateLike) return null
  const d = (typeof dateLike === 'string' || typeof dateLike === 'number')
    ? new Date(dateLike)
    : dateLike
  return d instanceof Date && !isNaN(d.getTime()) ? d : null
}

// MM.DD 포맷
function fmtMD(dateLike: any): string | null {
  const d = toDate(dateLike)
  if (!d) return null
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${mm}.${dd}`
}


// 마감일 후보 키 탐색 (있으면 사용)
function getEnd(a: T) {
  return a.end_date ?? null
}

// 출력: "MM.DD~" 또는 "MM.DD~MM.DD"
function dateRange(a: T) {
  const start = fmtMD(a.start_date)
  const due = fmtMD(getEnd(a))
  if (start && due) return `${start}~${due}`
  if (start) return `${start}~`
  if (due) return `~${due}`
  return '—'
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
    status: statusValue(a.status),
    task_type: a.task_type?.value ?? a.task_type,
    assignees_json: a.assignees_json ?? a.assignees ?? [],
  }
  open.value = true
}

function onSaved(updated: T) {
  if (!props.actions) return
  const idx = props.actions.findIndex(x => x.id === updated.id)
  if (idx >= 0) props.actions[idx] = { ...props.actions[idx], ...updated }
  emit('saved', updated)
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

      <!-- 상태(공통 라벨) + 날짜 범위 -->
      <div class="flex items-center gap-2 mt-2 text-xs">
        <span
          class="inline-flex items-center px-2 py-0.5 rounded-full font-medium"
          :class="STATUS_CLASS[statusValue(a.status)]"
        >
          {{ STATUS_LABEL[statusValue(a.status)] }}
        </span>
        <!-- ⬇️ 여기만 변경: '시작 yyyy.mm.dd' -> 'MM.DD~[MM.DD]' -->
        <span class="text-gray-500">{{ dateRange(a) }}</span>
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
