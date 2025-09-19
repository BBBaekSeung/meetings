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
      업로드
    </button>

    <!-- ✅ 브라우저 녹음(준실시간) -->
    <div class="pt-3 border-t mt-3 space-y-2">
      <div class="text-sm font-medium">브라우저 녹음(준실시간)</div>
      <div class="flex gap-2">
        <button
          class="px-3 py-1 rounded-xl border"
          @click="startRecord"
          :disabled="recBusy || recState !== 'idle'"
        >
          녹음 시작
        </button>
        <button
          class="px-3 py-1 rounded-xl border"
          @click="stopRecord"
          :disabled="recBusy || recState !== 'recording'"
        >
          녹음 종료
        </button>
        <button
          class="px-3 py-1 rounded-xl border"
          @click="goDetail"
          :disabled="!mid"
        >
          상태 보기
        </button>
      </div>
      <div class="text-sm">
        상태: {{ recState }} · 전송 청크: {{ sentChunks }}
        <span v-if="recMsg" class="ml-2 text-gray-600">{{ recMsg }}</span>
        <span v-if="recErr" class="ml-2 text-red-600">오류: {{ recErr }}</span>
      </div>
    </div>

    <div v-if="msg" class="text-sm">{{ msg }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { uploadToMeeting, uploadChunk, finalizeRecording } from '../lib/api'
import { useMeeting } from '../composables/useMeeting'

const route = useRoute()
const router = useRouter()

const mid = computed(() => String(route.query.mid || ''))
const t = computed(() => String(route.query.t || ''))
const { data: meeting, isLoading: meetingLoading, error: meetingError } = useMeeting(mid)


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
    // ✅ 모바일은 안내 문구만
    msg.value = '업로드 완료! 데스크톱 화면에서 자동으로 결과가 표시됩니다.'
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

    // 2초 간격으로 청크 전송
    mediaRecorder.start(3000)
  } catch (e: any) {
    recErr.value = e?.message || '마이크 권한 거부 또는 초기화 실패'
  }
}

async function stopRecord() {
  if (recState.value !== 'recording' || !mediaRecorder) return
  recBusy.value = true
  recState.value = 'finalizing'
  recMsg.value = '처리 시작...'

  try {
    // 녹음 중지 → 마지막 dataavailable 발생
    mediaRecorder.stop()

    // 너무 복잡한 이벤트 대기 로직 대신 짧게 대기(마지막 청크 전송 여유)
    await new Promise((r) => setTimeout(r, 300))
  } catch {
    /* noop */
  } finally {
    // 마이크 해제(간단 정리)
    try {
      streamRef?.getTracks().forEach((t) => t.stop())
    } catch {}
    streamRef = null
    mediaRecorder = null
  }

  try {
    await finalizeRecording(mid.value, t.value)
    recMsg.value = '처리가 시작되었습니다. 상태 보기로 이동해 확인하세요.'
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
</script>
