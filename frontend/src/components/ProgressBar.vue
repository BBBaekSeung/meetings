<template>
  <div class="w-full bg-gray-200 rounded-2xl h-3 overflow-hidden">
    <div class="h-3 rounded-2xl bg-black transition-all duration-500" :style="{ width: `${clamped}%` }" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ value: number }>()
const clamped = computed(() => Math.min(100, Math.max(0, props.value ?? 0)))
</script>
