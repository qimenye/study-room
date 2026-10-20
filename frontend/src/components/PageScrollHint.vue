<script setup>
import { computed } from 'vue'

import AppIcon from './AppIcon.vue'

const props = defineProps({
  target: { type: Object, default: null },
  arrow: { type: String, default: 'down' }, // down = 下一页，up = 上一页
  progress: { type: Number, default: 0 },
})

defineEmits(['go'])

const up = computed(() => props.arrow === 'up')
const active = computed(() => props.progress > 0.02)
</script>

<template>
  <Transition name="page">
    <div
      v-if="target"
      class="pointer-events-none fixed inset-x-0 z-30 flex justify-center px-4"
      :class="up ? 'top-[4.6rem] max-sm:hidden' : 'bottom-5'"
    >
      <button
        class="scroll-hint pointer-events-auto group"
        :class="[
          active ? 'border-calm/60 text-calm' : 'opacity-75 hover:opacity-100',
          up ? 'py-1.5' : '',
        ]"
        @click="$emit('go')"
      >
        <span class="relative flex h-6 w-6 items-center justify-center">
          <svg viewBox="0 0 36 36" class="absolute inset-0 h-6 w-6 -rotate-90">
            <circle cx="18" cy="18" r="15" fill="none" stroke="rgba(148,163,184,0.25)" stroke-width="3" />
            <circle
              cx="18"
              cy="18"
              r="15"
              fill="none"
              stroke="currentColor"
              stroke-width="3"
              stroke-linecap="round"
              class="transition-[stroke-dashoffset] duration-300 ease-out"
              :stroke-dasharray="94.2"
              :stroke-dashoffset="94.2 * (1 - Math.min(1, progress))"
            />
          </svg>
          <AppIcon
            :name="up ? 'chevronUp' : 'chevronDown'"
            :size="13"
            :class="up ? 'animate-nudge-up' : 'animate-nudge'"
          />
        </span>
        <span class="whitespace-nowrap">
          {{ up ? '继续向上滚动返回' : '继续向下滚动进入' }}
          <span class="font-medium text-slate-100 group-hover:text-calm">{{ target.label }}</span>
        </span>
      </button>
    </div>
  </Transition>
</template>
