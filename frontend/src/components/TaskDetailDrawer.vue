<template>
  <!-- Overlay -->
  <div v-if="modelValueProxy" class="fixed inset-0 z-40" @click.self="close">
    <div class="absolute inset-0 bg-black/40"></div>

    <!-- Drawer (Task Card 스타일) -->
    <div
      class="absolute right-0 top-0 h-full w-full sm:w-[640px] bg-white dark:bg-zinc-900 z-50 shadow-2xl
             rounded-none sm:rounded-l-2xl flex flex-col"
    >

      <!-- Header -->
      <div class="px-5 py-4 border-b flex items-center gap-2">
        <div class="text-[18px] font-semibold truncate leading-6">
          <template v-if="editingTitle">
            <input
              v-model="draftTitle"
              class="border rounded px-2 py-1 text-base font-semibold bg-white dark:bg-zinc-900"
              @keyup.enter="saveEditTitle"
              @keydown.esc="cancelEditTitle"
              @blur="cancelEditTitle"
              autofocus
            />
            <button
              class="ml-2 px-2.5 py-1.5 rounded-lg border text-sm hover:bg-gray-50"
              type="button"
              @mousedown.prevent="saveEditTitle"
            >
              저장
            </button>
          </template>
          <template v-else>
            <span class="cursor-pointer" @click="startEditTitle" title="제목 수정">
              {{ headerTitle }}
            </span>
          </template>
        </div>
        <span class="ml-auto text-sm text-gray-500"></span>
        <button class="ml-2 px-2.5 py-1.5 rounded-lg border text-sm hover:bg-gray-50" @click="close">닫기</button>
      </div>

      <!-- Body -->
      <div class="p-5 space-y-5 overflow-auto">
        <!-- 프로젝트 / 업무 유형 -->
        <CardSection>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">

            <FormBox label="업무 유형">
              <div class="relative">
                <select v-model="local.task_type" class="input pr-10 appearance-none">
                  <option>일반</option>
                  <option>체크리스트</option>
                  <option>데이터 취합</option>
                  <option>투표</option>
                </select>
                <span class="icon-right">▾</span>
              </div>
            </FormBox>
          </div>
        </CardSection>

        <!-- 진행 상태 -->
        <CardSection>
          <FormBox label="진행 상태">
            <div class="flex gap-2 flex-wrap">
              <Chip
                v-for="s in statuses"
                :key="s.value"
                :active="local.status===s.value"
                :variant="s.value"
                :tw-active="STATUS_BADGE_TW[s.value]"
                :tw-inactive="'bg-gray-100 text-gray-400 border border-gray-200'"
                @click="local.status=s.value"
              >
                {{ s.label }}
              </Chip>
            </div>
          </FormBox>
        </CardSection>

        <!-- 날짜 + 작업 시간 -->
        <CardSection>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormBox label="시작일">
              <div class="relative">
                <input type="date" v-model="local.start_date" class="input pr-10" />
                <span class="icon-right">📅</span>
              </div>
            </FormBox>

            <FormBox label="종료일">
              <div class="relative">
                <input type="date" v-model="local.end_date" class="input pr-10" />
                <span class="icon-right">📅</span>
              </div>
            </FormBox>

            <FormBox label="완료일">
              <div class="relative">
                <input type="date" v-model="local.completed_date" class="input pr-10" />
                <span class="icon-right">📅</span>
              </div>
            </FormBox>

            <FormBox label="작업 시간">
              <div class="relative inline-block w-full">
                <input
                  v-model="local.work_time"
                  placeholder="예) 2:00 또는 120(분)"
                  class="input pr-10"
                />
                <span class="icon-right">⏱</span>
              </div>
            </FormBox>
          </div>
        </CardSection>

        <!-- 담당자/관람자 -->
        <CardSection>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormBox label="작업자">
              <TagInput v-model="local.assignees" placeholder="이름 입력 후 Enter" editable />
            </FormBox>
            <FormBox label="관람자">
              <TagInput v-model="local.watchers" placeholder="이름 입력 후 Enter" editable />
            </FormBox>
          </div>
        </CardSection>

        <!-- 중요도 -->
        <CardSection>
          <FormBox label="중요도">
            <div class="flex gap-2 flex-wrap">
              <Chip :active="local.priority==='낮음'"  @click="local.priority='낮음'" variant="low">낮음</Chip>
              <Chip :active="local.priority==='보통'"  @click="local.priority='보통'" variant="normal">보통</Chip>
              <Chip :active="local.priority==='높음'"  @click="local.priority='높음'" variant="warn">높음</Chip>
              <Chip :active="local.priority==='긴급'"  @click="local.priority='긴급'" variant="danger">긴급</Chip>
            </div>
          </FormBox>
        </CardSection>

        <!-- 메모 -->
        <CardSection>
          <FormBox label="메모">
            <textarea v-model="local.note" rows="4" class="input h-auto"></textarea>
          </FormBox>
        </CardSection>

        <!-- 체크리스트 -->
        <CardSection v-if="local.task_type === '체크리스트'">
          <div class="flex items-center justify-between mb-2">
            <div class="text-sm font-semibold">체크리스트</div>
            <div class="text-xs text-gray-500">{{ doneCount }}/{{ checklist.length }}</div>
          </div>

          <div class="flex gap-2 mb-2">
            <input
              v-model="newItem"
              @keydown.enter.prevent="addChecklistItem"
              placeholder="항목을 입력해주세요"
              class="input flex-1"
            />
            <button type="button" class="btn-ghost" @click="addChecklistItem">추가</button>
          </div>

          <div v-if="loadingChecklist" class="text-sm text-gray-500">불러오는 중…</div>
          <ul v-else class="space-y-2">
            <li v-for="it in checklist" :key="it.id" class="flex items-center gap-2 rounded-xl border px-3 py-2">
              <input type="checkbox" :checked="it.is_done" @change="e => toggleItem(it, (e.target as HTMLInputElement).checked)">
              <input
                :value="it.label"
                @change="e => renameItem(it, (e.target as HTMLInputElement).value)"
                class="flex-1 bg-transparent outline-none"
              />
              <button type="button" class="text-gray-500 hover:text-red-600" @click="removeItem(it)">🗑</button>
            </li>
            <li v-if="checklist.length === 0" class="text-sm text-gray-500 px-1">항목이 없습니다.</li>
          </ul>
        </CardSection>

        <!-- 투표 -->
        <CardSection v-else-if="local.task_type === '투표'">
          <VoteCreateDrawer
            v-if="mode === 'create'"
            :meeting-id="props.meetingId"
            :task-id="local.id"
            @started="onVoteStarted"
            @saved="(p) => emit('saved', p)"
            @closed="onVoteClosed"
          />
          <div v-else-if="mode === 'open'" class="space-y-6">
            <template v-if="vote?.my_option_id">
              <!-- ✅ 본인 투표 완료 → 결과 즉시 표시 -->
              <VoteResult :meeting-id="props.meetingId" :task-id="local.id" />
            </template>
            <template v-else>
              <VoteRunner
                :meeting-id="props.meetingId"
                :task-id="local.id"
                :voter="currentUserId"
                @voted="refreshVote()"      
              />
            </template>
            <VoteManagePanel :meeting-id="props.meetingId" :task-id="local.id" />
          </div>
          <VoteResult v-else-if="mode === 'closed'" :meeting-id="props.meetingId" :task-id="local.id" />
        </CardSection>
      </div>

      <!-- Footer -->
      <div class="mt-auto p-4 border-t bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60">
        <div class="flex justify-end gap-2">
          <button class="btn-ghost" @click="close">닫기</button>
          <button class="btn-primary" @click="save" :disabled="saving">
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
import { type TaskStatus, STATUS_BADGE_TW } from '../task' // ← .ts 확장자 제거

import {
  listChecklist,
  addChecklist,
  patchChecklist,
  deleteChecklist,
  type ChecklistItem
} from '../lib/checklist'

/* ---- 투표 관련 import ---- */
import VoteCreateDrawer from '../components/vote/VoteCreateDrawer.vue'
import VoteManagePanel from '../components/vote/VoteManagePanel.vue'
import VoteRunner from '../components/vote/VoteRunner.vue'
import VoteResult from '../components/vote/VoteResult.vue'

import { getVote, closeVote, cancelVote } from '../lib/vote' // startVote 미사용이라 제거
import type { VoteSummary } from '../lib/vote'

/* -------------------- props/emits -------------------- */
const props = defineProps<{
  modelValue: boolean
  meetingId: string
  task: any
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
const local = reactive<any>({
  id: null,
  title: '',
  note: '',
  status: 'in_progress',
  task_type: '일반',
  start_date: null as string | null,
  end_date: null as string | null,
  completed_date: null as string | null,
  work_time: '',
  assignees: [] as string[],
  watchers: [] as string[],
  priority: '보통' as string | null,
  project: '',
})

/* -------------------- 제목 인라인 편집 상태/로직 -------------------- */
const editingTitle = ref(false)
const draftTitle = ref('')

function startEditTitle() {
  if (!props.task) return
  // ↓ 기본값 '주간업무보고 템플릿' 제거
  draftTitle.value = (local.title || '').trim()
  editingTitle.value = true
}


async function saveEditTitle() {
  if (!props.meetingId || local.id == null) { editingTitle.value = false; return }
  const newTitle = draftTitle.value.trim()
  const curTitle = (local.title || '').trim()
  if (!newTitle || newTitle === curTitle) { editingTitle.value = false; return }
  try {
    const { data } = await api.patch(`/meetings/${props.meetingId}/actions/${local.id}`, { title: newTitle })
    local.title = data?.title ?? newTitle
    emit('saved', data || { id: local.id, title: local.title })
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? e.message ?? '제목 저장 실패')
  } finally {
    editingTitle.value = false
  }
}
function cancelEditTitle() {
  // blur로 바로 빠져나간 경우, 저장하지 않고 편집 종료
  editingTitle.value = false
}

/* ---------------- 투표 상태 관리 ---------------- */
const mode = ref<'create' | 'open' | 'closed'>('create')
const vote = ref<any>(null)
const currentUserId = 'user-123' // TODO: 실제 로그인 사용자 ID 주입

function onVoteStarted(summary: VoteSummary) {
  // ✅ 로컬 분기 키를 즉시 '투표'로 전환해야 화면이 그대로 투표 섹션을 유지합니다.
  local.task_type = '투표'

  // 저장 직후 서버 재호출 없이 즉시 반영
  vote.value = summary
  mode.value = summary.is_open ? 'open' : (summary.total_votes > 0 ? 'closed' : 'create')
}
function onVoteClosed() {
  // 서버는 이미 DONE으로 바뀌었을 것. 로컬도 맞춰서
  local.status = 'done'
  mode.value = 'closed'
}

async function refreshVote() {
  if (!props.meetingId || !local.id) return
  try {
    const v = await getVote(props.meetingId, local.id, currentUserId)
    vote.value = v
    if (v.is_open) mode.value = 'open'
    else if (v.total_votes > 0) mode.value = 'closed'
    else mode.value = 'create'
  } catch (e: any) {
    // 아직 투표 미시작이거나 레이스 → 'create'
    if (e?.response?.status === 409) {
      mode.value = 'create'
      vote.value = null
      return
    }
    mode.value = 'create'
  }
}

watch(
  () => [props.meetingId, local.id] as const,
  async () => {
    // 태스크가 로드/변경될 때만 서버 상태를 보고 모드 결정
    if (props.meetingId && local.id && local.task_type === '투표') {
      await refreshVote()
    } else {
      mode.value = 'create'
      vote.value = null
    }
  },
  { immediate: true }
)

/* -------------------- 체크리스트 상태/로직 -------------------- */
const checklist = ref<ChecklistItem[]>([])
const newItem = ref('')
const loadingChecklist = ref(false)
const doneCount = computed(() => checklist.value.filter(x => x.is_done).length)

async function refreshChecklist() {
  const mid = props.meetingId
  const id = local.id
  const tt = local.task_type
  if (!mid || id == null || tt !== '체크리스트') {
    checklist.value = []
    return
  }
  loadingChecklist.value = true
  try {
    checklist.value = await listChecklist(mid, id)
  } finally {
    loadingChecklist.value = false
  }
}

async function addChecklistItem() {
  if (!props.meetingId || local.id == null) return
  if (!newItem.value?.trim()) return
  try {
    await addChecklist(props.meetingId, local.id, newItem.value.trim())
    newItem.value = ''
    await refreshChecklist()
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '추가 실패'
    alert(`체크리스트 추가 실패: ${msg}`)
  }
}

async function toggleItem(it: ChecklistItem, checked: boolean) {
  console.debug('[toggleItem] mid', props.meetingId, 'taskId', local.id, 'itemId', it.id, 'checked', checked)
  try {
    await patchChecklist(props.meetingId, local.id, it.id as any, { is_done: checked })
  } catch (e: any) {
    console.error('[toggleItem] patch error', e?.response?.status, e?.response?.data || e)
    alert(`체크 실패: ${e?.response?.data?.detail || e.message}`)
  }
}

async function renameItem(it: ChecklistItem, label: string) {
  if (!props.meetingId || local.id == null) return
  const saved = await patchChecklist(props.meetingId, local.id, it.id, { label })
  Object.assign(it, saved)
}
async function removeItem(it: ChecklistItem) {
  if (!props.meetingId || local.id == null) return
  await deleteChecklist(props.meetingId, local.id, it.id)
  checklist.value = checklist.value.filter(x => x.id !== it.id)
}

watch(
  () => [props.meetingId, local.id, local.task_type] as const,
  () => { void refreshChecklist() },
  { immediate: true }
)

/* ---------- 날짜 유틸 등 ---------- */
function toYMD(v: any): string | null {
  if (!v) return null
  if (typeof v === 'string') {
    const m = v.match(/^\d{4}-\d{2}-\d{2}/)
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

/** 헤더 제목 */
const headerTitle = computed(() => (local.title ?? '').trim())

watch(() => props.task, (t) => {
  if (!t) return
  local.id = t.id ?? null
  local.title = t.title ?? ''
  local.note = t.note ?? ''
  local.status = (t.status?.value ?? t.status ?? local.status ?? 'in_progress')
  local.task_type = t.task_type ?? '일반'
  local.start_date     = toYMD(t.start_date)
  local.end_date       = toYMD(t.end_date)
  local.completed_date = toYMD(t.completed_date)
  local.work_time = toWorkTimeString(t.work_time_min)
   // ✅ 배열 우선: assignees → assignees_json → assignee → owner
 local.assignees = normalizeNames(
   t.assignees ?? t.assignees_json ?? t.assignee ?? t.owner ?? []
 )
  local.watchers = normalizeNames(t.watchers_json ?? [])
  local.priority = t.priority ?? local.priority
  local.project = t.project ?? local.project
}, { immediate: true })

/* -------------------- helpers -------------------- */
const statuses : { value: TaskStatus, label: string }[] = [
  { value: 'todo',        label: '요청' },
  { value: 'in_progress', label: '진행' },
  { value: 'feedback',    label: '피드백' },
  { value: 'on_hold',     label: '보류' },
  { value: 'canceled',    label: '취소' },
  { value: 'done',        label: '완료' },
]
function close(){ modelValueProxy.value = false }
const saving = ref(false)

async function save() {
  if (!props.meetingId || local.id == null) return
  saving.value = true
  try {
    const wasVote = props.task?.task_type === '투표'
    const toNonVote = local.task_type !== '투표' // ← 체크리스트뿐 아니라 '일반' 등 모두 포함

    if (wasVote && toNonVote) {
      try {
        const v = await getVote(props.meetingId, local.id, currentUserId)
        // 1) 열려 있으면 먼저 닫고
        if (v?.is_open) {
          await closeVote(props.meetingId, local.id)
        }
        // 2) 존재 자체를 제거(취소)
        await cancelVote(props.meetingId, local.id)

        // 필요시 상태 동기화
        // local.status = 'done'
      } catch (e) {
        // 투표 미시작/이미 취소 상태면 그냥 통과
        console.debug('[vote teardown]', e)
      }
    }

    const payload = toPatchPayload(local, props.task)
    let data

    try {
      ({ data } = await api.patch(`/meetings/${props.meetingId}/actions/${local.id}`, payload))
    } catch (e: any) {
      // 혹시나 타이밍 이슈로 409가 오면 단계적 축소 재시도
      if (e?.response?.status === 409 && wasVote && toNonVote) {
        const p1: any = { ...payload }; delete p1.task_type
        try {
          ({ data } = await api.patch(`/meetings/${props.meetingId}/actions/${local.id}`, p1))
        } catch (e2: any) {
          if (e2?.response?.status === 409) {
            const p2: any = { ...p1 }; delete p2.status
            ;({ data } = await api.patch(`/meetings/${props.meetingId}/actions/${local.id}`, p2))
          } else {
            throw e2
          }
        }
      } else {
        throw e
      }
    }

    // 응답 반영
    Object.assign(local, {
      title: data.title ?? local.title,
      note: data.note ?? local.note,
      status: data.status ?? local.status,
      task_type: data.task_type ?? local.task_type,
      start_date: toYMD(data.start_date) ?? local.start_date,
      end_date: toYMD(data.end_date) ?? local.end_date,
      completed_date: toYMD(data.completed_date) ?? local.completed_date,
      work_time: toWorkTimeString(data.work_time_min),
      assignees: normalizeNames(data.assignees ?? data.assignees_json ?? local.assignees),
      watchers: normalizeNames(data.watchers ?? data.watchers_json ?? local.watchers),
      priority: data.priority ?? local.priority,
      project: data.project ?? local.project,
    })
    emit('saved', data)

  } catch (e: any) {
    console.error('[PATCH task] error', e?.response?.status, e?.response?.data)
    alert(e?.response?.data?.detail ?? e.message ?? '저장 실패')
  } finally {
    saving.value = false
  }
}

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
function shallowEqual(a: any, b: any) {
  if (Array.isArray(a) && Array.isArray(b)) return a.join('|') === b.join('|')
  return a === b
}

function toPatchPayload(x: any, original: any){
  const toMinutes = (v: string | null | undefined) => {
    if (!v) return null
    const s = String(v).trim()
    if (/^\d+:\d{2}$/.test(s)) { const [h,m]=s.split(':').map(Number); return h*60+m }
    if (/^\d+$/.test(s)) return Number(s)
    return null
  }

  const base = {
    title: x.title,
    note: x.note,
    status: x.status,
    task_type: x.task_type,
    start_date: x.start_date || null,
    end_date: x.end_date || null,
    completed_date: x.completed_date || null,
    work_time_min: toMinutes(x.work_time),
    assignees: x.assignees,
    watchers: x.watchers,
    priority: x.priority,
    project: x.project,
  }

  const diff: Record<string, any> = {}
  for (const k of Object.keys(base)) {
    const cur = (base as any)[k]
    const prev = (k === 'work_time_min') ? (original?.work_time_min ?? null) : original?.[k]
    if (!shallowEqual(cur, prev)) diff[k] = cur
  }

  // 실제 바뀌지 않았다면 task_type/status는 보내지 않음 (정책 충돌 최소화)
  if (diff.task_type === undefined) delete diff.task_type
  if (diff.status === undefined) delete diff.status

  return diff
}

/* -------------------- Inline components -------------------- */
const CardSection = defineComponent({
  name: 'CardSection',
  setup(_, { slots }) {
    return () => h('div', { class: 'rounded-2xl border bg-white/70 p-4 divide-y-0' }, slots.default?.())
  }
})


const FormBox = defineComponent({
  name: 'FormBox',
  props: { label: { type: String, required: true } },
  setup(p, { slots }) {
    return () => h('div', null, [
      h('div', { class: 'text-[12px] text-gray-500 mb-1' }, p.label),
      slots.default?.(),
    ])
  }
})

const Chip = defineComponent({
  name: 'Chip',
  props: {
    active: { type: Boolean, default: false },
    variant: { type: String as PropType<'todo'|'in_progress'|'feedback'|'on_hold'|'canceled'|'done'|'normal'|'warn'|'danger'|'low'|string>, default: '' },
    twActive: { type: String, default: '' },   // 외부 주입(카드와 동일 클래스)
    twInactive: { type: String, default: '' }, // 비활성 클래스
  },
  emits: ['click'],
  setup(p, { slots, emit }) {
    const onClick = (e: MouseEvent) => { e.stopPropagation(); emit('click') }

    const fallbackByVariant = (v: string) => {
      switch (v) {
        // 중요도
        case 'low':    return 'chip-gray'
        case 'normal': return 'chip-blue'
        case 'warn':   return 'chip-orange'
        case 'danger': return 'chip-red'
      }
    }
    const ACTIVE_TYPO = 'font-bold text-white rounded-full px-3 py-1 text-[13px]'
    const INACTIVE_TYPO = 'rounded-full px-3 py-1 text-[13px]'

    const classes = computed(() => {
      if (p.active) {
        const activeClass = p.twActive || fallbackByVariant(p.variant)
        return ['chip', ACTIVE_TYPO, activeClass].filter(Boolean).join(' ')
      }
      return ['chip', INACTIVE_TYPO, p.twInactive || 'bg-gray-100 text-gray-500 border border-gray-200'].join(' ')
    })
    return () => h('button', { class: classes.value, onClick }, slots.default?.())
  }
})

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
    const cancelEdit = () => { editIndex.value = null; editText.value = '' }

    const onKeyNew = (e: KeyboardEvent) => { if (e.key === 'Enter') { e.preventDefault(); add() } }
    const onKeyEdit = (e: KeyboardEvent) => {
      if (e.key === 'Enter') { e.preventDefault(); commitEdit() }
      if (e.key === 'Escape') { e.preventDefault(); cancelEdit() }
    }

    return () => h('div', { class: 'input p-2' }, [
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
/* ---- 공통 색상/치수 ---- */
:root{
  --border:#e5e7eb;      /* gray-200 */
  --text:#111827;        /* gray-900 */
  --muted:#6b7280;       /* gray-500 */
  --muted-2:#9ca3af;     /* gray-400 */
  --bg-soft:rgba(255,255,255,.6);
}

/* 입력 공통 */
.input{
  width:100%;
  padding:.5rem .75rem;
  border:1px solid var(--border);
  border-radius:.75rem;
  background:var(--bg-soft);
  font-size:14px;
  color:var(--text);
  outline:none;
  transition:border-color .15s ease, box-shadow .15s ease, background .15s ease;
}
.input:focus{
  border-color:#000;
  box-shadow:0 0 0 3px rgba(0,0,0,.06);
}
.input::placeholder{ color:var(--muted-2); }

/* 우측 아이콘(달력/시계) */
.icon-right{
  position:absolute; right:.75rem; top:50%;
  transform:translateY(-50%);
  color:var(--muted-2);
  pointer-events:none;
  font-size:14px;
}

/* 칩 버튼 */
.chip{
  padding:.375rem .75rem;
  border-radius:9999px;
  font-size:.875rem;
  border:1px solid transparent;
  transition:opacity .15s ease, transform .05s ease;
  cursor:default;
}
.chip:active{ transform:translateY(1px); }
.chip-green  { background:#22c55e; border-color:#22c55e; color:#fff; }  /* 요청 */
.chip-amber  { background:#f59e0b; border-color:#f59e0b; color:#fff; }  /* 진행 */
.chip-gray   { background:#9ca3af; border-color:#9ca3af; color:#fff; }  /* 완료 */
.chip-blue   { background:#3b82f6; border-color:#3b82f6; color:#fff; }  /* 보통 */
.chip-orange { background:#fb923c; border-color:#fb923c; color:#fff; }  /* 높음 */
.chip-red    { background:#dc2626; border-color:#dc2626; color:#fff; }  /* 긴급 */
.chip-teal   { background:#14b8a6; border-color:#14b8a6; color:#fff; }
.chip-black  { background:#000;    border-color:#000;    color:#fff; }

/* 카드 섹션(박스) */
:where(.dark) .card{ background:#0b0b0b; }
.card{
  border:1px solid var(--border);
  border-radius:1rem;
  background:rgba(255,255,255,.7);
  padding:1rem;
}

/* 상단 탭 */

/* 버튼 */
.btn-ghost{
  padding:.5rem 1rem;
  border:1px solid var(--border);
  border-radius:.75rem;
  background:#fff;
  color:#111827;
}
.btn-ghost:hover{ background:#f9fafb; }

.btn-primary{
  padding:.5rem 1rem;
  border:1px solid #000;
  border-radius:.75rem;
  background:#000;
  color:#fff;
  opacity:1;
  transition:opacity .15s ease, transform .05s ease;
}
.btn-primary:disabled{ opacity:.6; cursor:not-allowed; }
.btn-primary:active{ transform:translateY(1px); }

/* 라벨 캡션 */
:where(.form-label){ font-size:12px; color:#6b7280; margin-bottom:.25rem; }

/* 태그 입력 내부 토큰 */
.tag{
  display:inline-flex; align-items:center; gap:.25rem;
  padding:.25rem .5rem; border-radius:.5rem;
  background:#f3f4f6;
  font-size:.875rem;
}
.tag-remove{ color:#6b7280; }
</style>
