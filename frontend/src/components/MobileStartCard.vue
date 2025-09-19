<!-- src/components/MobileStartCard.vue -->
<template>
  <div class="p-6 rounded-2xl border space-y-4">
    <h2 class="text-xl font-semibold">모바일로 업로드</h2>
    <button class="px-4 py-2 rounded-xl border" @click="handle">QR 생성</button>
    <div v-if="err" class="text-red-600 text-sm">{{ err }}</div>

    <div v-if="mobile" class="space-y-3">
      <div class="text-sm">Meeting ID: {{ mobile.id }}</div>
      <a class="underline text-sm" :href="mobile.mobile_url" target="_blank">모바일 업로드 열기</a>
      <img :src="mobile.qr_data_uri" alt="QR for mobile upload" class="w-48 h-48" />

      <div class="text-xs text-gray-500">
        상태 감지 중… (업로드가 시작되면 자동으로 이동합니다)
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { createMeeting } from '../lib/api'
import { useMeeting } from '../composables/useMeeting' // ✅ 반응형 ID 받는 버전

const router = useRouter()
const mobile = ref<{ id: string; mobile_url: string; qr_data_uri: string }|null>(null)
const err = ref('')

const meetingId = ref('')                 // 처음엔 빈 값
const meetingQuery = useMeeting(meetingId) // ✅ ref 그대로 전달
const statusRef = computed(() => meetingQuery.data.value?.status)

// ✅ 여기 이 watch가 "자동 이동" 담당입니다.
watch(statusRef, (status) => {
  if (!status) return
  if (status === 'processing' || status === 'completed') {
    router.push(`/meetings/${meetingId.value}`)
  }
})

async function handle(){
  err.value = ''
  try {
    const m = await createMeeting('mobile')
    if (!m.mobile_url || !m.qr_data_uri) throw new Error('모바일 URL/QR 누락')
    mobile.value = { id: m.id, mobile_url: m.mobile_url, qr_data_uri: m.qr_data_uri }
    meetingId.value = m.id               // ✅ 여기서부터 폴링 시작
  } catch (e:any) {
    err.value = e.message || '생성 실패'
  }
}
</script>
