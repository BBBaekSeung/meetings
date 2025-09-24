<script setup lang="ts">
import { ref } from 'vue'
import VoteEditor from './VoteEditor.vue'
import { startVote } from '../../lib/vote'

const props = defineProps<{ meetingId: string; taskId: number }>()
const emit = defineEmits<{
  (e: 'started'): void
  (e: 'saved', payload: { id: number; status?: string }): void
}>()

const voteModel = ref({ title: '', options: [] as string[], deadline: null as string | null })
const saving = ref(false)

async function saveAndStart() {
  if (!voteModel.value.title || voteModel.value.options.length < 2) {
    alert('제목과 최소 2개의 항목이 필요합니다.')
    return
  }
  saving.value = true
  try {
    await startVote(props.meetingId, props.taskId, {
      options: voteModel.value.options,
      close_at: voteModel.value.deadline,
    })
    emit('started') // TaskDetailDrawer에서 refreshVote() 호출
    emit('saved', { id: props.taskId, status: 'in_progress' }) // 리스트 상태 갱신용
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
