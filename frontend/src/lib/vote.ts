// src/lib/vote.ts
import { api } from './api'

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

export async function startVote(
  meetingId: string,
  taskId: number,
  payload: { options: string[]; close_at?: string | null }
) {
  const { data } = await api.post(
    `/meetings/${meetingId}/actions/${taskId}/vote/start`,
    payload
  )
  return data as VoteSummary   // ← 백엔드 응답(VoteSummaryOut)을 그대로 돌려줌
}

export async function getVote(meetingId: string, taskId: number, voter?: string): Promise<VoteSummary> {
  const { data } = await api.get(`/meetings/${meetingId}/actions/${taskId}/vote`, {
    params: voter ? { voter } : undefined,
  })
  return data as VoteSummary
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
