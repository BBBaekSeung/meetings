<!-- src/pages/MobileUploadPage.vue -->
<template>
  <div class="max-w-lg mx-auto p-6 space-y-4">
    <h1 class="text-2xl font-semibold">모바일 업로드</h1>
    <div class="text-sm text-gray-600">{{ meeting?.name || mid }}</div>

    <!-- 파일 업로드 -->
    <input
      type="file"
      accept="audio/*,video/mp4,video/quicktime"
      @change="onFile"
    />
    <button
      class="px-4 py-2 rounded-xl border"
      @click="handle"
      :disabled="loading || !file"
    >
      Upload
    </button>


    <div v-if="msg" class="text-sm">{{ msg }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { uploadToMeeting, uploadChunk, finalizeRecording, api } from '../lib/api'
import { useMeeting } from '../composables/useMeeting'

const route = useRoute()
const router = useRouter()

const mid = computed(() => String(route.query.mid || ''))
const t = computed(() => String(route.query.t || ''))
const { data: meeting } = useMeeting(mid)

// ---- 파일 업로드 ----
const file = ref<File | null>(null)
const loading = ref(false)
const msg = ref('')

function onFile(e: Event) {
  const el = e.target as HTMLInputElement
  file.value = el.files?.[0] || null
}

async function handle() {
  if (!mid.value || !t.value || !file.value) return
  loading.value = true
  msg.value = '업로드 중...'
  try {
    await uploadToMeeting(mid.value, t.value, file.value)
    // ✅ 업로드 성공 후 최종 메시지
    msg.value = '완료되었습니다. 데스크탑에서 확인하세요.'
  } catch (e: any) {
    msg.value = e?.message || '업로드 실패'
  } finally {
    loading.value = false
  }
}

// ====== ✅ 브라우저 녹음(준실시간 청크) ======
type RecState = 'idle' | 'recording' | 'finalizing'
const recState = ref<RecState>('idle')
const recBusy = ref(false)
const sentChunks = ref(0)
const recErr = ref('')
const recMsg = ref('')

let mediaRecorder: MediaRecorder | null = null
let streamRef: MediaStream | null = null
let seq = 0

function pickMime(): string {
  const cands = ['audio/webm;codecs=opus', 'audio/webm']
  for (const m of cands) {
    if ((window as any).MediaRecorder?.isTypeSupported?.(m)) return m
  }
  return '' // 브라우저 기본값 사용
}

async function startRecord() {
  recErr.value = ''
  recMsg.value = ''
  if (!mid.value || !t.value) {
    recErr.value = '잘못된 접근입니다. (mid/t 누락)'
    return
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    recErr.value = '브라우저가 오디오 캡처를 지원하지 않습니다.'
    return
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    streamRef = stream
    const mime = pickMime()
    mediaRecorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined)

    seq = 0
    sentChunks.value = 0
    recState.value = 'recording'
    recMsg.value = '녹음을 시작했습니다.'

    mediaRecorder.ondataavailable = async (e: BlobEvent) => {
      if (!e.data || !e.data.size) return
      try {
        await uploadChunk(mid.value, t.value, seq++, e.data)
        sentChunks.value++
      } catch (ex: any) {
        recErr.value = ex?.message || '청크 업로드 실패'
        stopRecord()
      }
    }

    // 3초 간격으로 청크 전송
    mediaRecorder.start(3000)
  } catch (e: any) {
    recErr.value = e?.message || '마이크 권한 거부 또는 초기화 실패'
  }
}

async function stopRecord() {
  if (recState.value !== 'recording' || !mediaRecorder) return
  recBusy.value = true
  recState.value = 'finalizing'
  // ✅ 100% 이후 사용자에게 '처리중..' 단계가 보이도록
  recMsg.value = '처리중.. (업로드 100%)'

  try {
    // 녹음 중지 → 마지막 dataavailable 발생
    mediaRecorder.stop()
    // 마지막 청크 전송 여유
    await new Promise((r) => setTimeout(r, 300))
  } catch {
    /* noop */
  } finally {
    // 마이크 해제
    try {
      streamRef?.getTracks().forEach((t) => t.stop())
    } catch {}
    streamRef = null
    mediaRecorder = null
  }

  try {
    await finalizeRecording(mid.value, t.value)
    // ✅ 처리 완료 알림
    recMsg.value = '완료되었습니다. 데스크탑에서 확인하세요.'
    // 필요 시 토스트/알림 컴포넌트 사용 가능
    // alert('업로드가 완료되었습니다! 데스크탑에서 확인해주세요.')
    router.push(`/meetings/${mid.value}`)
  } catch (e: any) {
    recErr.value = e?.message || 'finalize 실패'
  } finally {
    recBusy.value = false
    recState.value = 'idle'
  }
}

function goDetail() {
  if (mid.value) router.push(`/meetings/${mid.value}`)
}

// ✅ 데스크탑에서 지정한 회의 이름을 모바일에서도 반영
onMounted(async () => {
  const incomingName = String(route.query.name || '').trim()
  if (mid.value && incomingName) {
    // meeting.name이 비어있을 때만 패치
    if (!meeting.value?.name) {
      try {
        await api.patch(`/meetings/${mid.value}`, { name: incomingName })
      } catch (e) {
        console.warn('회의 이름 PATCH 실패', e)
      }
    }
  }
})
</script>
