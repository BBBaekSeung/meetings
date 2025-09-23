<template>
  <div class="border rounded-xl p-4 h-96 overflow-auto bg-white">
    <pre class="whitespace-pre-wrap leading-7 text-sm font-mono m-0">
{{ text || '아직 전체 스크립트가 없습니다.' }}
    </pre>
  </div>
  <div v-if="error" class="text-sm text-red-600 mt-2">{{ error }}</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useQuery, type QueryKey } from '@tanstack/vue-query'
import { getFullscript } from '../lib/api'

const props = defineProps<{ meetingId: string; enabled?: boolean }>()
const key = computed<QueryKey>(() => ['fullscript', props.meetingId] as const)

const q = useQuery<string>({
  queryKey: key,
  queryFn: () => getFullscript(props.meetingId),
  enabled: computed(() => Boolean(props.meetingId) && (props.enabled ?? true)),
  refetchOnWindowFocus: false,
})

const text = computed(() => q.data.value || '')
const error = computed(() => (q.error.value as any)?.message || '')
</script>
