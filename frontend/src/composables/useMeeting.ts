
// src/composables/useMeeting.ts
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, unref, type MaybeRef } from 'vue'
import { getMeeting } from '../lib/api'
import type { Meeting } from '../lib/types'
import { listMeetings } from '../lib/api'

export function useMeeting(meetingId: MaybeRef<string>) {
  const queryClient = useQueryClient()
  const id = computed(() => unref(meetingId))
  const key = computed(() => ['meeting', id.value])  // ✅ 항상 같은 키 형태 사용

  return useQuery<Meeting>({
    queryKey: key,
    queryFn: async () => {
      const cached = queryClient.getQueryData<Meeting>(key.value)
      const view: 'brief' | 'full' =
        cached && cached.status !== 'completed' ? 'brief' : 'full'

      // 1) 먼저 brief 또는 full을 요청
      const res = await getMeeting(id.value, view)

      // 2) brief 로 받았는데 완료면, 즉시 full로 승격 페치 + 캐시에 저장
      if (view === 'brief' && res.status === 'completed') {
        try {
          const full = await getMeeting(id.value, 'full')
          queryClient.setQueryData(key.value, full)  // ✅ 승격 저장
          return full
        } catch {
          // full 실패 시, 일단 brief라도 반환(다음 폴링에서 재시도)
          return res
        }
      }

      return res
    },

    // 폴링: 진행 중엔 2.5s, 1분 후 5s, 완료/실패 stop
    refetchInterval: (q) => {
      const m = q.state.data as Meeting | undefined
      if (!m) return 2500
      if (m.status === 'completed' || m.status === 'failed') return false
      const elapsed = Date.now() - q.state.dataUpdatedAt
      return elapsed > 60_000 ? 5000 : 2500
    },

    refetchOnWindowFocus: false,
    enabled: () => !!id.value,
    staleTime: 0,          // ✅ 함수 안 됨: 고정값으로
    gcTime: 10 * 60_000,   // (선택) 캐시 유지 시간
  })
}



export function useMeetings(params?: {
  q?: string
  limit?: number
  offset?: number
  order?: 'asc' | 'desc'
}) {
  return useQuery<Meeting[]>({
    queryKey: ['meetings', params || {}],
    queryFn: () => listMeetings(params),
    staleTime: 10_000,
    refetchOnWindowFocus: false,
  })
}
