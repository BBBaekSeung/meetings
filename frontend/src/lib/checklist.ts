// frontend/src/lib/checklist.ts
import { api } from './api'

export type ChecklistItem = {
  id: number
  label: string
  is_done: boolean
  order: number
  created_at: string
  updated_at: string
}

export async function listChecklist(mid: string, taskId: number) {
  const { data } = await api.get<ChecklistItem[]>(
    `/meetings/${mid}/actions/${taskId}/checklist-items`
  )
  return data
}

export async function addChecklist(mid: string, taskId: number, label: string) {
  const { data } = await api.post<ChecklistItem>(
    `/meetings/${mid}/actions/${taskId}/checklist-items`,
    { label }
  )
  return data
}

export async function patchChecklist(
  mid: string,
  taskId: number,
  itemId: number,
  payload: Partial<Pick<ChecklistItem, 'label' | 'is_done' | 'order'>>
) {
  const { data } = await api.patch<ChecklistItem>(
    `/meetings/${mid}/actions/${taskId}/checklist-items/${itemId}`,
    payload
  )
  return data
}

export async function deleteChecklist(mid: string, taskId: number, itemId: number) {
  await api.delete(`/meetings/${mid}/actions/${taskId}/checklist-items/${itemId}`)
}
