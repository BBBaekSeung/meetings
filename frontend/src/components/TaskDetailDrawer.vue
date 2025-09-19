<template>
  <!-- Overlay -->
  <div v-if="modelValueProxy" class="fixed inset-0 z-40" @click.self="close">
    <div class="absolute inset-0 bg-black/40"></div>

    <!-- Drawer -->
    <div
      class="absolute right-0 top-0 h-full w-full sm:w-[560px] bg-white dark:bg-zinc-900 z-50 shadow-2xl
             rounded-none sm:rounded-l-2xl flex flex-col"
    >
      <!-- Header -->
      <div class="p-5 border-b flex items-center gap-2">
        <div class="text-lg font-semibold truncate">
          {{ headerTitle }}
        </div>
        <span class="ml-auto text-sm text-gray-500" v-if="meetingId">#{{ meetingId }}</span>
        <button class="ml-2 px-2 py-1 rounded-lg border text-sm" @click="close">닫기</button>
      </div>

      <!-- Body -->
      <div class="p-5 space-y-4 overflow-auto">
        <!-- 프로젝트 / 업무 유형 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <FormBox label="프로젝트">
            <input
              v-model="local.project"
              placeholder="예) Cloud Tech LABs 업무보고"
              class="w-full px-3 py-2 rounded-xl border bg-white/60"
            />
          </FormBox>

          <FormBox label="업무 유형">
            <div class="relative">
              <select
                v-model="local.task_type"
                class="w-full appearance-none px-3 py-2 rounded-xl border bg-white/60 pr-9"
              >
                <option>일반</option>
                <option>체크리스트</option>
                <option>데이터 취합</option>
                <option>투표</option>
              </select>
              <span class="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">▾</span>
            </div>
          </FormBox>
        </div>

        <!-- 진행 상태 칩 -->
        <FormBox label="진행 상태">
          <div class="flex gap-2 flex-wrap">
            <Chip
              v-for="s in statuses"
              :key="s.value"
              :active="local.status===s.value"
              :variant="s.value"
              @click="local.status=s.value"
            >
              {{ s.label }}
            </Chip>
          </div>
        </FormBox>

        <!-- 날짜 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <FormBox label="시작일">
            <div class="relative">
              <input type="date" v-model="local.start_date" class="w-full px-3 py-2 rounded-xl border pr-9" />
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">📅</span>
            </div>
          </FormBox>
          <FormBox label="종료일">
            <div class="relative">
              <input type="date" v-model="local.end_date" class="w-full px-3 py-2 rounded-xl border pr-9" />
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">📅</span>
            </div>
          </FormBox>
          <FormBox label="완료일">
            <div class="relative">
              <input type="date" v-model="local.completed_date" class="w-full px-3 py-2 rounded-xl border pr-9" />
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">📅</span>
            </div>
          </FormBox>
          <FormBox label="기한">
            <div class="relative">
              <input type="date" v-model="local.due_date" class="w-full px-3 py-2 rounded-xl border pr-9" />
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">📅</span>
            </div>
          </FormBox>
        </div>

        <!-- 작업 시간 -->
        <FormBox label="작업 시간">
          <div class="relative inline-block">
            <input
              v-model="local.work_time"
              placeholder="예) 2:00 또는 120(분)"
              class="w-44 px-3 py-2 rounded-xl border pr-9"
            />
            <span class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">⏱</span>
          </div>
        </FormBox>

        <!-- 담당자/관람자 -->
        <FormBox label="작업자">
          <TagInput v-model="local.assignees" placeholder="이름 입력 후 Enter" editable />
        </FormBox>
        <FormBox label="관람자">
          <TagInput v-model="local.watchers" placeholder="이름 입력 후 Enter" editable />
        </FormBox>

        <!-- 중요도 -->
        <FormBox label="중요도">
          <div class="flex gap-2 flex-wrap">
            <Chip :active="local.priority==='낮음'"  @click="local.priority='낮음'">낮음</Chip>
            <Chip :active="local.priority==='보통'"  @click="local.priority='보통'" variant="normal">보통</Chip>
            <Chip :active="local.priority==='높음'"  @click="local.priority='높음'" variant="warn">높음</Chip>
            <Chip :active="local.priority==='긴급'"  @click="local.priority='긴급'" variant="danger">긴급</Chip>
          </div>
        </FormBox>

        <!-- 메모 -->
        <FormBox label="메모">
          <textarea v-model="local.note" rows="4" class="w-full px-3 py-2 rounded-xl border"></textarea>
        </FormBox>
      </div>

      <!-- Footer -->
      <div class="mt-auto p-4 border-t bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60">
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 rounded-xl border" @click="close">닫기</button>
          <button class="px-4 py-2 rounded-xl border bg-black text-white disabled:opacity-60" @click="save" :disabled="saving">
            {{ saving ? '저장 중…' : '저장' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineComponent, h, reactive, watch, computed, ref } from 'vue'
import type { PropType } from 'vue'
import { api } from '../lib/api'

// 날짜 유틸
function toYMD(v: any): string | null {
  if (!v) return null
  if (typeof v === 'string') {
    const m = v.match(/^\d{4}-\d{2}-\d{2}/)   // '2025-09-17' or '2025-09-17T...'
    if (m) return m[0]
    const d = new Date(v)
    if (!isNaN(d.getTime())) {
      const tz = d.getTimezoneOffset() * 60 * 1000
      return new Date(d.getTime() - tz).toISOString().slice(0, 10)
    }
    return null
  }
  if (v instanceof Date && !isNaN(v.getTime())) {
    const tz = v.getTimezoneOffset() * 60 * 1000
    return new Date(v.getTime() - tz).toISOString().slice(0, 10)
  }
  return null
}




/* -------------------- props/emits -------------------- */
const props = defineProps<{
  modelValue: boolean
  meetingId: string
  task: any // actions[i] or tasks row
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'saved', payload: any): void
}>()

const modelValueProxy = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit('update:modelValue', v),
})

/* -------------------- local form state -------------------- */
/** 기본값: 진행(in_progress), 중요도 보통 */
const local = reactive<any>({
  id: null,
  title: '',
  note: '',
  status: 'in_progress',
  task_type: '일반',
  start_date: null as string | null,
  end_date: null as string | null,
  due_date: null as string | null,
  completed_date: null as string | null,
  work_time: '',                // "2:00" 또는 "90"
  assignees: [] as string[],
  watchers: [] as string[],
  priority: '보통' as string | null,
  project: '',
})

/** 헤더 제목: 템플릿 느낌 */
const headerTitle = computed(() =>
  local.title?.trim()
    ? local.title
    : '주간업무보고 템플릿'
)

watch(() => props.task, (t) => {
  if (!t) return
  local.id = t.id ?? null
  local.title = t.title ?? ''
  local.note = t.note ?? ''
  local.status = t.status ?? local.status
  local.task_type = t.task_type ?? '일반'
  local.start_date     = toYMD(t.start_date)       // ★ 여기
  local.end_date       = toYMD(t.end_date)
  local.due_date       = toYMD(t.due ?? t.due_date)
  local.completed_date = toYMD(t.completed_date)
  local.work_time = toWorkTimeString(t.work_time_min)
  local.assignees = normalizeNames(t.assignees_json ?? t.owner ?? [])
  local.watchers = normalizeNames(t.watchers_json ?? [])
  local.priority = t.priority ?? local.priority
  local.project = t.project ?? local.project
}, { immediate: true })

/* -------------------- UI helpers -------------------- */
const statuses = [
  { value: 'todo',        label: '요청' },
  { value: 'in_progress', label: '진행' },
  { value: 'done',        label: '완료' },
]

function close(){ modelValueProxy.value = false }

const saving = ref(false)
async function save(){
  if (!props.meetingId || local.id == null) return close()
  saving.value = true
  try {
    const payload = toPatchPayload(local)
    const { data } = await api.patch(
      `/meetings/${props.meetingId}/actions/${local.id}`,
      payload
    )
    emit('saved', data)
    close()
  } finally {
    saving.value = false
  }
}

/* -------------------- utils -------------------- */
function normalizeNames(v: any): string[] {
  if (Array.isArray(v)) return v.map(x => String(x).trim()).filter(Boolean)
  if (typeof v === 'string') {
    return v
      .split(/[,&/·]|(?:\s+(?:및|그리고|와|과)\s+)/)
      .map(s => s.trim())
      .filter(Boolean)
  }
  return []
}
function toWorkTimeString(min?: number): string {
  if (!min && min !== 0) return ''
  const h = Math.floor(min/60), m = min%60
  return `${h}:${String(m).padStart(2,'0')}`
}
function toPatchPayload(x: any){
  return {
    title: x.title,
    note: x.note,
    status: x.status,
    task_type: x.task_type,
    start_date: x.start_date || null,
    end_date: x.end_date || null,
    due_date: x.due_date || null,
    completed_date: x.completed_date || null,
    work_time: x.work_time || null, // 서버가 "1:30"/"90" 모두 파싱
    assignees: x.assignees,
    watchers: x.watchers,
    priority: x.priority,
    project: x.project,
  }
}

/* -------------------- inline sub-components -------------------- */
const FormBox = defineComponent({
  name: 'FormBox',
  props: { label: { type: String, required: true } },
  setup(p, { slots }) {
    return () => h('div', null, [
      h('div', { class: 'text-xs text-gray-500 mb-1' }, p.label),
      slots.default?.(),
    ])
  }
})

const Chip = defineComponent({
  name: 'Chip',
  props: {
    active: { type: Boolean, default: false },
    /** variant: 상태/우선순위 색상 */
    variant: { type: String as PropType<'todo'|'in_progress'|'done'|'normal'|'warn'|'danger'|string>, default: '' }
  },
  emits: ['click'],
  setup(p, { slots, emit }) {
    const onClick = (e: MouseEvent) => { e.stopPropagation(); emit('click') }
    const color = computed(() => {
      if (!p.active) return 'bg-white hover:bg-gray-50 border'
      switch (p.variant) {
        case 'in_progress': return 'bg-orange-500 text-white border-orange-500'
        case 'done':        return 'bg-gray-400 text-white border-gray-400'
        case 'todo':        return 'bg-green-500 text-white border-green-500'
        case 'warn':        return 'bg-amber-500 text-white border-amber-500'
        case 'danger':      return 'bg-red-600 text-white border-red-600'
        case 'normal':      return 'bg-blue-500 text-white border-blue-500'
        default:            return 'bg-black text-white border-black'
      }
    })
    return () => h('button', {
      class: [
        'px-3 py-1.5 rounded-full text-sm transition border',
        color.value
      ],
      onClick
    }, slots.default?.())
  }
})

/**
 * TagInput with inline edit:
 * - Enter로 추가
 * - 태그 클릭 시 인라인 입력으로 전환 후 Enter/Blur로 저장, Esc 취소
 */
const TagInput = defineComponent({
  name: 'TagInput',
  props: {
    modelValue: { type: Array as PropType<string[]>, default: () => [] },
    placeholder: { type: String, default: '추가…' },
    editable: { type: Boolean, default: false },
  },
  emits: ['update:modelValue'],
  setup(p, { emit }) {
    const txt = ref('')
    const editIndex = ref<number|null>(null)
    const editText = ref('')

    const add = () => {
      const v = txt.value.trim()
      if (!v) return
      if (!p.modelValue.includes(v)) emit('update:modelValue', [...p.modelValue, v])
      txt.value = ''
    }
    const remove = (i: number) => {
      const next = p.modelValue.filter((_, idx) => idx !== i)
      emit('update:modelValue', next)
    }

    const startEdit = (i: number) => {
      if (!p.editable) return
      editIndex.value = i
      editText.value = p.modelValue[i]
    }
    const commitEdit = () => {
      if (editIndex.value === null) return
      const i = editIndex.value
      const v = editText.value.trim()
      const next = [...p.modelValue]
      next[i] = v || next[i]
      emit('update:modelValue', next)
      editIndex.value = null
      editText.value = ''
    }
    const cancelEdit = () => {
      editIndex.value = null
      editText.value = ''
    }

    const onKeyNew = (e: KeyboardEvent) => {
      if (e.key === 'Enter') { e.preventDefault(); add() }
    }
    const onKeyEdit = (e: KeyboardEvent) => {
      if (e.key === 'Enter') { e.preventDefault(); commitEdit() }
      if (e.key === 'Escape') { e.preventDefault(); cancelEdit() }
    }

    return () => h('div', { class: 'border rounded-xl p-2' }, [
      h('div', { class: 'flex gap-2 flex-wrap' }, [
        ...p.modelValue.map((n, i) =>
          editIndex.value === i
            ? h('input', {
                class: 'px-2 py-1 rounded-lg border min-w-[120px]',
                value: editText.value,
                onInput: (e: any) => editText.value = e.target.value,
                onBlur: commitEdit,
                onKeydown: onKeyEdit,
                autofocus: true
              })
            : h('span', {
                class: 'px-2 py-1 rounded-lg bg-gray-100 text-sm flex items-center gap-1 cursor-text',
                onClick: () => startEdit(i)
              }, [
                n,
                h('button', {
                  class: 'text-gray-500',
                  onClick: (ev: MouseEvent) => { ev.stopPropagation(); remove(i) }
                }, '×')
              ])
        ),
        h('input', {
          class: 'flex-1 min-w-[140px] outline-none',
          placeholder: p.placeholder,
          value: txt.value,
          onInput: (e: any) => txt.value = e.target.value,
          onKeydown: onKeyNew
        })
      ])
    ])
  }
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity .15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
