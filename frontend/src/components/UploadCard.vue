<template>
  <div class="p-6 rounded-2xl border space-y-4">
    <h2 class="text-xl font-semibold">데스크톱에서 업로드</h2>
    <button class="px-4 py-2 rounded-xl border" @click="handleCreate" :disabled="loading">
      회의 생성
    </button>

    <template v-if="meetingId">
      <div class="space-y-3">
        <input type="file" accept="audio/*,video/mp4,video/quicktime" @change="onFile" />
        <button class="px-4 py-2 rounded-xl border" @click="handleUpload" :disabled="loading || !file">
          Upload
        </button>
        <!-- ✅ 신규: 브라우저 녹음(준실시간 청크) -->
        <div class="pt-3 border-t mt-3 space-y-2">
          <div class="text-sm font-medium">브라우저 녹음</div>
          <div class="flex gap-2">
            <button class="px-3 py-1 rounded-xl border" @click="startRecord" :disabled="recBusy || recState!=='idle'">녹음 시작</button>
            <button class="px-3 py-1 rounded-xl border" @click="stopRecord" :disabled="recBusy || recState!=='recording'">녹음 종료</button>
            <button class="px-3 py-1 rounded-xl border" @click="goDetail" :disabled="!meetingId">Upload</button>
          </div>
          
        </div>
      </div>
    </template>
  </div>
</template>






<script setup lang="ts">
import { ref } from 'vue'
import { createMeeting, uploadToMeeting, uploadChunk, finalizeRecording } from '../lib/api'
import { useRouter } from 'vue-router'


const props = defineProps<{ meetingName?: string }>()

const router = useRouter()
const file = ref<File|null>(null)
const token = ref('')
const loading = ref(false)
const meetingId = ref<string|null>(null)

function onFile(e: Event) {
  const t = e.target as HTMLInputElement
  file.value = t.files?.[0] || null
}

async function handleCreate() {
  loading.value = true
  try {
    const m = await createMeeting('web', props.meetingName)
    meetingId.value = m.id
    token.value = m.upload_token || ''
  } finally {
    loading.value = false
  }
}

async function handleUpload() {
  if (!meetingId.value || !file.value || !token.value) return
  loading.value = true
  try {
    await uploadToMeeting(meetingId.value, token.value, file.value)
    router.push(`/meetings/${meetingId.value}`)
  } finally {
    loading.value = false
  }
}

function goDetail() {
  if (meetingId.value) router.push(`/meetings/${meetingId.value}`)
}

/* ====== ✅ 브라우저 녹음(준실시간 청크) ====== */
type RecState = 'idle'|'recording'|'finalizing'
const recState = ref<RecState>('idle')
const recBusy = ref(false)
const sentChunks = ref(0)
const recErr = ref('')
const recMsg = ref('')

let mediaRecorder: MediaRecorder | null = null
let stream: MediaStream | null = null
let seq = 0
let pending = 0
let stopping = false
let finalized = false

function pickMime(): string {
  const cands = ['audio/webm;codecs=opus', 'audio/webm']
  for (const m of cands) {
    if (window.MediaRecorder?.isTypeSupported?.(m)) return m
  }
  return ''
}

async function ensureMeeting() {
  if (!meetingId.value || !token.value) {
    const m = await createMeeting('web', props.meetingName)
    meetingId.value = m.id
    token.value = m.upload_token || ''
  }
}

function sleep(ms:number){ return new Promise(r=>setTimeout(r,ms)) }
async function waitUntil(cond: ()=>boolean, timeoutMs=15000, tick=100){
  const start = Date.now()
  while (!cond()) {
    if (Date.now()-start>timeoutMs) break
    await sleep(tick)
  }
}

async function startRecord(){
  recErr.value = ''; recMsg.value = ''
  pending = 0; stopping = false; finalized = false
  sentChunks.value = 0; seq = 0

  await ensureMeeting()
  if (!navigator.mediaDevices?.getUserMedia) {
    recErr.value = '브라우저가 오디오 캡처를 지원하지 않습니다.'
    return
  }

  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mime = pickMime()
    mediaRecorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined)

    mediaRecorder.ondataavailable = async (e: BlobEvent) => {
      if (!e.data || !e.data.size) return
      if (finalized) return
      pending++
      try {
        await uploadChunk(meetingId!.value!, token.value, seq++, e.data)
        sentChunks.value++
      } catch (ex:any) {
        // stop 과정에서 늦게 온 청크 403은 무시 가능
        if (!stopping) {
          recErr.value = ex?.message || '청크 업로드 실패'
        }
      } finally {
        pending--
      }
    }

    mediaRecorder.start(3000) // 2초 청크
    recState.value = 'recording'
    recMsg.value = '녹음을 시작했습니다.'
  } catch (e:any) {
    recErr.value = e?.message || '마이크 권한 거부 또는 초기화 실패'
    try { stream?.getTracks().forEach(t=>t.stop()) } catch {}
    stream = null
    mediaRecorder = null
  }
}

async function stopRecord(){
  if (recState.value !== 'recording' || !mediaRecorder) return
  recBusy.value = true
  recState.value = 'finalizing'
  recMsg.value = '마지막 청크 정리 중...'
  stopping = true

  try {
    // 마지막 chunk 강제 방출
    try { mediaRecorder.requestData() } catch {}
    try { mediaRecorder.stop() } catch {}

    // 마이크 스트림 해제
    try { stream?.getTracks().forEach(t=>t.stop()) } catch {}
    stream = null

    // ✅ finalize 전에 '현재 토큰'을 안전하게 스냅샷
    const tokenSnapshot = token.value

    // ✅ 업로드 대기: pending==0 될 때까지 + 200ms 추가 여유
    await waitUntil(() => pending === 0, 20000, 100)
    await sleep(200)

    if (sentChunks.value <= 0) {
      recErr.value = '전송된 청크가 없습니다. (마이크 입력/권한을 확인하세요)'
      return
    }

    // ✅ 여기서 finalize (스냅샷 토큰 사용)
    await finalizeRecording(meetingId!.value!, tokenSnapshot)

    // finalize 이후엔 토큰 비워서 추가 청크 전송 방지
    token.value = ''
    recMsg.value = '처리를 시작했습니다. 상태 보기로 이동해 확인하세요.'
  } catch (e:any) {
    recErr.value = e?.message || 'finalize 실패'
  } finally {
    recBusy.value = false
    recState.value = 'idle'
    mediaRecorder = null
  }
}


</script>
