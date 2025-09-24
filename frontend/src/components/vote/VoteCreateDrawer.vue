<script setup lang="ts">
import { ref } from 'vue'
import VoteEditor from './VoteEditor.vue'
import { startVote } from '../../lib/vote'
import type { VoteSummary } from '../../lib/vote'   // ✅ 응답 타입 가져오기

const props = defineProps<{ meetingId: string; taskId: number }>()
const emit = defineEmits<{
  (e: 'started', summary: VoteSummary): void   // ✅ 요약을 같이 올림
  (e: 'saved', payload: { id: number; status?: string }): void
}>()

const voteModel = ref({ options: [] as string[], deadline: null as string | null })
const saving = ref(false)

async function saveAndStart() {
  const opts = voteModel.value.options.map(o => o.trim()).filter(Boolean)
  if (opts.length < 2) {
    alert('옵션은 최소 2개 이상이어야 합니다.')
    return
  }
  saving.value = true
  try {
    // ✅ startVote 응답을 받아서
    const summary = await startVote(props.meetingId, props.taskId, {
      options: opts,
      close_at: voteModel.value.deadline,
    })
    // ✅ 부모로 요약을 넘겨 즉시 반영(추가 GET 없이도 화면 갱신 가능)
    emit('started', summary)
    // 리스트(작업 카드) 등 외부 상태 갱신용 이벤트 그대로 유지
    emit('saved', { id: props.taskId, status: 'in_progress' })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <VoteEditor v-model="voteModel" />
    <button class="px-4 py-2 border rounded bg-black text-white" :disabled="saving" @click="saveAndStart">
      투표 시작
    </button>
  </div>
</template>
