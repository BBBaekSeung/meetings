<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getVote } from '../../lib/vote'

const props = defineProps<{ meetingId: string; taskId: number }>()
const vote = ref<any>(null)

async function refresh() {
  vote.value = await getVote(props.meetingId, props.taskId)
}
onMounted(refresh)
</script>

<template>
  <div v-if="vote" class="space-y-2">
    <h3>{{ vote.title }}</h3>
    <p class="text-sm text-gray-500">총 {{ vote.total_votes }}표</p>
    <div v-for="opt in vote.options" :key="opt.id">
      <div class="flex justify-between">
        <span>{{ opt.label }}</span>
        <span>{{ opt.votes }}</span>
      </div>
      <div class="h-2 bg-gray-200 rounded">
        <div class="h-2 bg-gray-600 rounded"
             :style="{width: ((opt.votes / Math.max(1,vote.total_votes))*100)+'%'}"></div>
      </div>
    </div>
  </div>
</template>
