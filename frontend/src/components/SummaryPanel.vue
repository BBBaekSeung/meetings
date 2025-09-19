<template>
  <div v-if="!summary || summary.length === 0" class="text-sm text-gray-500">요약이 아직 없습니다.</div>
  <div v-else class="space-y-4">
    <p v-for="(p, i) in summary" :key="i" class="leading-7">{{ p }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{ summary?: string[] }>()   // ✅ props 변수 미생성
</script>