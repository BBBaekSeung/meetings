<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getVote, closeVote, cancelVote } from '../../lib/vote'

const props = defineProps<{ meetingId: string; taskId: number }>()
const vote = ref<any>(null)

async function refresh() {
  vote.value = await getVote(props.meetingId, props.taskId)
}
onMounted(refresh)

async function doClose() {
  await closeVote(props.meetingId, props.taskId)
  await refresh()
}
async function doCancel() {
  await cancelVote(props.meetingId, props.taskId)
  await refresh()
}
</script>

<template>
  <div v-if="vote" class="space-y-3">
    <h3 class="font-medium">{{ vote.title }}</h3>
    <div v-if="vote.is_open" class="flex gap-2">
      <button class="px-3 py-1 border rounded" @click="doClose">투표 종료</button>
      <button class="px-3 py-1 border rounded" @click="doCancel">투표 취소</button>
    </div>
    <div v-else>종료됨 / 취소됨</div>
  </div>
</template>
