<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getVote, castVote } from '../../lib/vote'

const emit = defineEmits<{ (e: 'voted'): void }>()   // ✅ 추가
const props = defineProps<{ meetingId: string; taskId: number; voter: string }>()
const vote = ref<any>(null)
const selected = ref<number|null>(null)

async function refresh() {
  vote.value = await getVote(props.meetingId, props.taskId, props.voter)
  selected.value = vote.value.my_option_id
}
onMounted(refresh)

async function submit() {
  if (selected.value == null) return
  await castVote(props.meetingId, props.taskId, props.voter, selected.value)
  await refresh()
  emit('voted')   // ✅ 부모에게 알림 → 결과로 전환 트리거

}
</script>

<template>
  <div v-if="vote" class="space-y-3">
    <h3>{{ vote.title }}</h3>
    <div v-for="opt in vote.options" :key="opt.id" class="flex items-center gap-2">
      <input type="radio" :value="opt.id" v-model="selected" />
      <span>{{ opt.label }}</span>
    </div>
    <button class="px-3 py-1 border rounded bg-blue-600 text-white" @click="submit">투표</button>
  </div>
</template>
