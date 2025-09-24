// src/lib/vote.ts
import { api } from './api'  // ← checklist.ts와 같은 폴더라면 './api'가 맞습니다.

export interface VoteOption {
  id: number
  label: string
  votes: number
}

export interface VoteSummary {
  is_open: boolean
  close_at?: string | null
  my_option_id?: number | null
  total_votes: number
  options: VoteOption[]
}

export interface VoteStartPayload {
  options: string[]            // 최소 2개
  close_at?: string | null     // ISO8601 (예: '2025-10-01T12:00:00Z')
}


export async function startVote(
  meetingId: string,
  taskId: number,
  payload: { options: string[]; close_at?: string | null }
) {
  await api.post(`/meetings/${meetingId}/actions/${taskId}/vote/start`, payload)
}

export async function getVote(meetingId: string, taskId: number, voter?: string) {
  const { data } = await api.get(`/meetings/${meetingId}/actions/${taskId}/vote`, {
    params: voter ? { voter } : {},
  })
  return data
}

export async function castVote(meetingId: string, taskId: number, voter: string, option_id: number) {
  await api.post(`/meetings/${meetingId}/actions/${taskId}/vote/cast`, { voter, option_id })
}

export async function closeVote(meetingId: string, taskId: number) {
  await api.post(`/meetings/${meetingId}/actions/${taskId}/vote/close`, {})
}

export async function cancelVote(meetingId: string, taskId: number) {
  await api.post(`/meetings/${meetingId}/actions/${taskId}/vote/cancel`, {})
}
