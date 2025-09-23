// frontend/src/lib/checklist.ts
import { api } from '../lib/api'

export interface ChecklistItem {
  id: number
  label: string
  is_done: boolean
  order?: number | null
  created_at?: string
  updated_at?: string
}

/** 체크리스트 목록 */
export async function listChecklist(mid: string, taskId: number): Promise<ChecklistItem[]> {
  const { data } = await api.get<ChecklistItem[]>(
    `/meetings/${mid}/actions/${taskId}/checklist-items`
  )
  return data
}

export async function addChecklist(mid: string, taskId: number, label: string): Promise<ChecklistItem> {
  if (!label?.trim()) throw new Error('label is required')
  const { data } = await api.post<ChecklistItem>(
    `/meetings/${mid}/actions/${taskId}/checklist-items`,
    { label: label.trim() }   // JSON
  )
  return data
}

export async function patchChecklist(
  mid: string,
  taskId: number,
  itemId: number,
  payload: Partial<Pick<ChecklistItem, 'label' | 'is_done' | 'order'>>
): Promise<ChecklistItem> {
  const { data } = await api.patch<ChecklistItem>(
    `/meetings/${mid}/actions/${taskId}/checklist-items/${itemId}`,
    payload
  )
  return data
}

export async function deleteChecklist(mid: string, taskId: number, itemId: number): Promise<void> {
  await api.delete(`/meetings/${mid}/actions/${taskId}/checklist-items/${itemId}`)
}
