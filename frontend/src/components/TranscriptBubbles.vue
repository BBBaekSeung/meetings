<!-- src/components/TranscriptBubbles.vue -->
<script setup lang="ts">
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { getFullscript } from '../lib/api'

const props = defineProps<{ meetingId: string; enabled?: boolean }>()

const q = useQuery<string>({
  queryKey: computed(() => ['fullscript', props.meetingId] as const),
  queryFn: () => getFullscript(props.meetingId),
  enabled: computed(() => Boolean(props.meetingId) && (props.enabled ?? true)),
  refetchOnWindowFocus: false,
})

const lines = computed(() =>
  (q.data.value || '')
    .split('\n')
    .map(s => s.trim())
    .filter(Boolean)
)
</script>

<template>
  <div v-if="q.isPending.value" class="text-sm text-gray-500">스크립트 불러오는 중…</div>
  <div v-else-if="q.error.value" class="text-sm text-red-600">불러오기 실패: {{ (q.error.value as any)?.message || '에러' }}</div>

  <div v-else class="flex flex-col gap-2">
    <div
      v-for="(line, i) in lines"
      :key="i"
      class="max-w-[900px] w-fit rounded-2xl px-3 py-2 bg-gray-100"
    >
      <!-- '참가자N: 내용' 형식 가정 -->
      <template v-if="line.includes(':')">
        <span class="inline-flex items-center gap-1 text-xs font-medium text-gray-700 mr-2">
          <span class="inline-block w-1.5 h-1.5 rounded-full bg-gray-400"></span>
          {{ line.split(':', 1)[0] }}
        </span>
        <span class="text-sm text-gray-900">{{ line.slice(line.indexOf(':') + 1).trim() }}</span>
      </template>
      <template v-else>
        <span class="text-sm text-gray-900">{{ line }}</span>
      </template>
    </div>
  </div>
</template>
