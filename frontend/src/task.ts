export type TaskStatus = 'todo' | 'in_progress' | 'feedback' | 'on_hold' | 'canceled' | 'done'

export const STATUS_LABEL: Record<TaskStatus, string> = {
  todo: '요청',
  in_progress: '진행',
  feedback: '피드백',
  on_hold: '보류',
  canceled: '취소',
  done: '완료',
}

export const STATUS_OPTIONS: { value: TaskStatus; label: string }[] = [
  { value: 'todo',        label: STATUS_LABEL.todo },
  { value: 'in_progress', label: STATUS_LABEL.in_progress },
  { value: 'feedback',    label: STATUS_LABEL.feedback },
  { value: 'on_hold',     label: STATUS_LABEL.on_hold },
  { value: 'canceled',    label: STATUS_LABEL.canceled },
  { value: 'done',        label: STATUS_LABEL.done },
]

// 상태 → 태그/뱃지(라이트 톤) Tailwind 클래스 공통 매핑
export const STATUS_BADGE_TW: Record<TaskStatus, string> = {
  todo:        'bg-emerald-500 text-white font-bold rounded-full px-3 py-1',
  in_progress: 'bg-orange-400 text-white font-bold rounded-full px-3 py-1',
  feedback:    'bg-yellow-400 text-white font-bold rounded-full px-3 py-1',
  on_hold:     'bg-purple-400 text-white font-bold rounded-full px-3 py-1',
  canceled:    'bg-violet-300 text-white font-bold rounded-full px-3 py-1', 
  done:        'bg-blue-500 text-white font-bold rounded-full px-3 py-1',
}
