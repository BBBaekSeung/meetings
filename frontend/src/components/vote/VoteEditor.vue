<script setup lang="ts">
import { ref, watch } from 'vue'

interface VoteModel { title: string; options: string[]; deadline?: string | null }

const props = defineProps<{ modelValue: VoteModel }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: VoteModel): void }>()

const title = ref(props.modelValue.title || '')
const options = ref<string[]>(props.modelValue.options || [])
const newOpt = ref('')
const deadline = ref(props.modelValue.deadline || null)

function addOption() {
  const v = newOpt.value.trim()
  if (!v) return
  options.value.push(v)
  newOpt.value = ''
  pushModel()
}
function removeOption(i: number) {
  options.value.splice(i, 1)
  pushModel()
}
function pushModel() {
  emit('update:modelValue', { title: title.value.trim(), options: [...options.value], deadline: deadline.value })
}
watch([title, options, deadline], pushModel, { deep: true })
</script>

<template>
  <div class="space-y-4">
    <div>
      <label class="block text-sm text-gray-600">투표 제목</label>
      <input v-model="title" class="w-full border rounded px-3 py-2" placeholder="예: 회식 장소" />
    </div>

    <div>
      <label class="block text-sm text-gray-600">항목 추가</label>
      <div class="flex gap-2 mb-2">
        <input v-model="newOpt" @keydown.enter.prevent="addOption" class="flex-1 border rounded px-3 py-2" />
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
      <input type="datetime-local" v-model="deadline" class="border rounded px-3 py-2" />
    </div>
  </div>
</template>
