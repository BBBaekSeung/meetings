export type MeetingStatus = 'pending_upload'|'processing'|'completed'|'failed'

export interface Task {
  id: number
  meeting_id: string
  title: string
  assignee: string | null
  note: string | null
  status: 'todo'|'in_progress'|'feedback'|'on_hold'|'canceled'|'done'
  task_type: '일반'|'체크리스트'|'데이터 취합'|'투표'
  priority: '낮음'|'보통'|'높음'|'긴급'|null
  start_date?: string|null
  end_date?: string|null
  due_date?: string|null
  completed_date?: string|null
  work_time_min?: number
  assignees_json?: string[] | null
  watchers_json?: string[] | null
  created_at?: string
  updated_at?: string
}

export interface MeetingResult {
  transcript?: string
  segments?: any[]
  summary?: string[] // 3문단
  actions?: Array<{
    title: string
    owner: string | string[] | null
    due: string | null
    note?: string | null
    status: Task['status']
    task_type: Task['task_type']
  }>
  error?: string
}

export interface Meeting {
  id: string
  name: string
  status: MeetingStatus
  progress: number
  created_at?: string     
  updated_at?: string      
  upload_token?: string
  upload_token_expires_in?: number
  mobile_url?: string | null
  qr_data_uri?: string | null
  result?: MeetingResult | null
}