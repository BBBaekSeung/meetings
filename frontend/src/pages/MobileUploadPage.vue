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
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { uploadToMeeting,  } from '../lib/api'
import { useMeeting } from '../composables/useMeeting'

const route = useRoute()
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





</script>
