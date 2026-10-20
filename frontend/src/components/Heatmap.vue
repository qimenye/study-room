<script setup>
import { computed } from 'vue'

import { formatDuration } from '../utils/format'

const props = defineProps({
  days: { type: Array, default: () => [] },
  maxDuration: { type: Number, default: 0 },
})

const LEVELS = [
  'bg-white/[0.035]',
  'bg-teal-900/70',
  'bg-teal-700/75',
  'bg-teal-500/75',
  'bg-teal-300/90',
]

const weeks = computed(() => {
  const items = props.days || []
  if (!items.length) return []
  const first = new Date(items[0].date + 'T00:00:00')
  const offset = (first.getDay() + 6) % 7
  const cells = new Array(offset).fill(null).concat(items)
  const result = []
  for (let i = 0; i < cells.length; i += 7) result.push(cells.slice(i, i + 7))
  return result
})

function level(day) {
  if (!day || !day.duration) return 0
  const ratio = day.duration / (props.maxDuration || 1)
  if (ratio > 0.75) return 4
  if (ratio > 0.5) return 3
  if (ratio > 0.25) return 2
  return 1
}

function title(day) {
  if (!day) return ''
  return day.date + ' · ' + formatDuration(day.duration) + ' · ' + day.count + ' 次'
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex gap-[5px] overflow-x-auto pb-1">
      <div v-for="(week, index) in weeks" :key="index" class="flex flex-col gap-[5px]">
        <div
          v-for="(day, dayIndex) in week"
          :key="dayIndex"
          class="h-3.5 w-3.5 rounded-[4px] ring-1 ring-inset ring-white/[0.06] transition hover:ring-calm/60"
          :class="day ? LEVELS[level(day)] : 'bg-transparent'"
          :title="title(day)"
        />
      </div>
    </div>
    <div class="flex items-center gap-2 text-[11px] text-slate-500">
      <span>少</span>
      <span v-for="(item, index) in LEVELS" :key="index" class="h-3.5 w-3.5 rounded-[4px] ring-1 ring-inset ring-white/[0.06]" :class="item" />
      <span>多</span>
      <span class="ml-auto">每格 = 一天</span>
    </div>
  </div>
</template>