// lib/api.ts
import axios from 'axios'
import type { Meeting } from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60_000,
  headers: { Accept: 'application/json' },
})

export async function createMeeting(source: 'web'|'mobile' = 'web', name?: string) {
  const q = new URLSearchParams({ source })
  if (name && name.trim()) q.set('name', name.trim())
  const { data } = await api.post<Meeting>(`/meetings?${q.toString()}`)
  return data
}

export async function updateMeetingName(id: string, name: string) {
  const { data } = await api.patch(`/meetings/${id}`, { name })
  return data
}

export async function createMobileMeeting() {
  return createMeeting('mobile')
}

export async function getMeeting(id: string, view: 'brief' | 'full' = 'full') {
  const { data } = await api.get<Meeting>(`/meetings/${id}?view=${view}`)
  return data
}


// ✅ 헤더 수동 지정 제거 (브라우저가 boundary를 자동 추가)
export async function uploadToMeeting(id: string, token: string, file: File) {
  const form = new FormData()
  form.append('token', token)
  form.append('file', file)
  try {
    const { data } = await api.post(`/meetings/${id}/upload`, form)
    return data as { accepted: boolean }
  } catch (err: any) {
    throw friendlyErrorWithStatus(err)
  }
}

export async function reissueUploadToken(id: string) {
  const { data } = await api.post<{ id: string; upload_token: string; upload_token_expires_in: number }>(
    `/meetings/${id}/upload-token`
  )
  return data
}

// ---- error helpers ----
function toStatus(err: any): number | undefined {
  return err?.response?.status
}
function toDetail(err: any): string | undefined {
  return err?.response?.data?.detail
}

function friendlyErrorWithStatus(err: any): never {
  const status = toStatus(err)
  const detail = toDetail(err)

  // 공통 매핑
  if (status === 400 && detail === 'UPLOAD_INVALID_TYPE') {
    const e = new Error('지원하지 않는 파일 형식이에요. (mp3, wav, aac/m4a, mp4 권장)')
    ;(e as any).status = status
    throw e
  }
  if (status === 400 && detail === 'UPLOAD_TOO_LARGE') {
    const e = new Error('파일이 너무 커요. 서버 제한(MB)을 확인해주세요.')
    ;(e as any).status = status
    throw e
  }
  if (status === 403 && detail === 'INVALID_OR_EXPIRED_TOKEN') {
    const e = new Error('업로드 토큰이 만료되었어요. 토큰을 다시 발급받아 주세요.')
    ;(e as any).status = status
    throw e
  }
  if (status === 400 && detail === 'NO_PARTS') {
    const e = new Error('올라온 청크가 없습니다. 녹음을 다시 시도해 주세요.')
    ;(e as any).status = status
    throw e
  }
  if (status === 409 && detail === 'CANNOT_REISSUE_TOKEN_IN_CURRENT_STATE') {
    const e = new Error('현재 상태에서는 토큰을 재발급할 수 없어요. (녹음/처리 중인지 확인)')
    ;(e as any).status = status
    throw e
  }

  const e = new Error(err?.message || '요청 실패')
  ;(e as any).status = status
  throw e
}

// ---- chunk/finalize ----

// Blob.type이 빈 경우 기본값을 audio/webm으로 교정
async function normalizeWebmBlob(blob: Blob): Promise<Blob> {
  const type = blob.type && blob.type.includes('webm') ? blob.type : 'audio/webm'
  if (type === blob.type) return blob
  const ab = await blob.arrayBuffer()
  return new Blob([ab], { type })
}

function pad6(n: number) {
  return String(n).padStart(6, '0')
}

export async function uploadChunk(meetingId: string, token: string, seq: number, blob: Blob) {
  const form = new FormData()
  form.append('token', token)
  form.append('seq', String(seq))

  const webmBlob = await normalizeWebmBlob(blob)
  // ✅ 파일명은 .webm 고정 + 6자리 패딩
  form.append('file', webmBlob, `part_${pad6(seq)}.webm`)

  try {
    const { data } = await api.post(`/meetings/${meetingId}/chunk`, form)
    return data as { accepted: boolean; seq: number }
  } catch (err: any) {
    // 정지 과정에서의 403을 프론트에서 구분할 수 있도록 status 포함
    throw friendlyErrorWithStatus(err)
  }
}

export async function finalizeRecording(meetingId: string, token: string) {
  try {
    const { data } = await api.post(`/meetings/${meetingId}/finalize`, { token })
    return data as { accepted: boolean; id: string }
  } catch (err: any) {
    throw friendlyErrorWithStatus(err)
  }
}



export async function listMeetings(params?: {
  q?: string
  limit?: number
  offset?: number
  order?: 'asc' | 'desc'
  view?: 'brief' | 'full'
}) {
  const normalized = {
    ...params,
    view: params?.view?.toLowerCase() as 'brief' | 'full' ?? 'brief',
    order: params?.order?.toLowerCase() as 'asc' | 'desc' ?? 'desc',
    limit: params?.limit ?? 50,
  }

  const { data } = await api.get<Meeting[]>('/meetings', { params: normalized })
  return data
}


export async function getFullscript(meetingId: string): Promise<string> {
  const { data } = await api.get(`/meetings/${meetingId}/fullscript`, {
    responseType: 'text',
  })
  return data as string
}
