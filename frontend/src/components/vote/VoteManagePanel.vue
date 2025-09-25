<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getVote, closeVote } from '../../lib/vote'
const emit = defineEmits<{ (e: 'closed'): void }>()   // 부모 알림

const props = defineProps<{ meetingId: string; taskId: number }>()


const vote = ref<any>(null)
const loading = ref(false)

async function refresh() {
  loading.value = true
  try {
    // voter가 필요 없으면 생략 OK
    vote.value = await getVote(props.meetingId, props.taskId)
  } catch (e: any) {
    // 투표가 아직 없거나 409면 초기 상태 처리
    if (e?.response?.status === 409) vote.value = null
  } finally {
    loading.value = false
  }
}
onMounted(refresh)

async function doClose() {
  await closeVote(props.meetingId, props.taskId)
  emit('closed')         // ✅ 부모에서 local.status='done'으로 맞춤
  await refresh()
}
</script>

<template>
  <div v-if="vote" class="space-y-3">
    <h3 class="font-medium">{{ vote.title }}</h3>

    <div v-if="vote.is_open" class="flex gap-2">
      <button class="px-3 py-1 border rounded" :disabled="loading" @click="doClose">
        {{ loading ? '처리 중…' : '투표 종료' }}
      </button>
    </div>
    <div v-else class="text-gray-500">종료됨</div>
  </div>
  <div v-else class="text-sm text-gray-400">투표가 아직 시작되지 않았습니다.</div>
</template>
