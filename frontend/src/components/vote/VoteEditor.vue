<script setup lang="ts">
import { ref, watch } from 'vue'

type VoteModel = { options: string[]; deadline: string | null }

const props = defineProps<{ modelValue: VoteModel }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: VoteModel): void }>()

// 로컬 상태
const options = ref<string[]>([...(props.modelValue.options ?? [])])
// <input type="datetime-local">는 빈 문자열을 원하므로 string로 들고 있다가 emit할 때 null 변환
const deadlineStr = ref<string>(props.modelValue.deadline ?? '')

function pushModel() {
  emit('update:modelValue', {
    options: [...options.value],
    deadline: deadlineStr.value || null,
  })
}

function addOption() {
  const v = newOpt.value.trim()
  if (!v) return
  // (선택) 중복 방지
  if (options.value.includes(v)) return
  options.value.push(v)
  newOpt.value = ''
  pushModel()
}

function removeOption(i: number) {
  options.value.splice(i, 1)
  pushModel()
}

const newOpt = ref('')

// options/마감 변경을 부모로 반영
watch([options, deadlineStr], pushModel, { deep: true })
</script>

<template>
  <div class="space-y-4">
    <div>
      <label class="block text-sm text-gray-600">항목 추가</label>
      <div class="flex gap-2 mb-2">
        <input
          v-model="newOpt"
          @keydown.enter.prevent="addOption"
          class="flex-1 border rounded px-3 py-2"
          placeholder="항목을 입력해주세요"
        />
        <button class="px-3 py-2 border rounded" @click="addOption">+</button>
      </div>
      <ul>
        <li v-for="(opt,i) in options" :key="i" class="flex justify-between items-center mb-1">
          <span>{{ opt }}</span>
          <button class="text-red-500 text-xs" @click="removeOption(i)">삭제</button>
        </li>
      </ul>
    </div>

    <div>
      <label class="block text-sm text-gray-600">마감시각</label>
      <input
        type="datetime-local"
        v-model="deadlineStr"
        class="border rounded px-3 py-2"
      />
    </div>
  </div>
</template>
`
