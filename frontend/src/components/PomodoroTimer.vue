<script setup>
import { computed } from 'vue'

import AppIcon from './AppIcon.vue'
import { useTimerStore } from '../stores/timer'
import { formatClock } from '../utils/format'

const timer = useTimerStore()
defineEmits(['start', 'pause', 'resume', 'end'])

const presets = [
  { label: '25', mode: 'pomodoro', minutes: 25 },
  { label: '45', mode: 'pomodoro', minutes: 45 },
  { label: '正计时', mode: 'countup', minutes: 0 },
]

const RADIUS = 56
const CIRC = 2 * Math.PI * RADIUS
const dashOffset = computed(() => CIRC * (1 - timer.progress))
const canSwitchMode = computed(() => !timer.isActive)

const statusStyle = computed(() => {
  if (timer.status === 'running') return 'border-calm/45 bg-calm/10 text-calm'
  if (timer.status === 'paused') return 'border-warm/45 bg-warm/10 text-warm'
  return 'border-white/10 bg-white/[0.05] text-slate-400'
})

const isPresetActive = (preset) =>
  timer.mode === preset.mode && (preset.mode === 'countup' || timer.plannedMinutes === preset.minutes)
</script>

<template>
  <div class="card relative flex flex-col items-center gap-5 overflow-hidden">
    <div class="flex w-full items-center justify-between">
      <span class="flex items-center gap-1.5 text-sm text-slate-400">
        <AppIcon name="clock" :size="15" />
        专注计时
      </span>
      <span class="rounded-full border px-2.5 py-0.5 text-[11px]" :class="statusStyle">
        {{ timer.statusText }}
      </span>
    </div>

    <div class="relative">
      <svg width="132" height="132" viewBox="0 0 132 132" class="-rotate-90">
        <defs>
          <linearGradient id="timerRing" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#7ff5df" />
            <stop offset="100%" stop-color="#38bdf8" />
          </linearGradient>
        </defs>
        <circle cx="66" cy="66" :r="RADIUS" fill="none" stroke="rgba(148,163,184,0.16)" stroke-width="9" />
        <circle
          cx="66"
          cy="66"
          :r="RADIUS"
          fill="none"
          stroke="url(#timerRing)"
          stroke-width="9"
          stroke-linecap="round"
          :stroke-dasharray="CIRC"
          :stroke-dashoffset="timer.mode === 'pomodoro' ? dashOffset : 0"
          class="transition-[stroke-dashoffset] duration-500"
        />
      </svg>
      <div class="absolute inset-0 flex flex-col items-center justify-center">
        <span class="num text-[28px] font-semibold leading-none text-slate-50 glow-text">
          {{ formatClock(timer.displaySeconds) }}
        </span>
        <span class="mt-1.5 text-[11px] text-slate-500">
          {{ timer.mode === 'countup' ? '已专注' : '剩余时间' }}
        </span>
      </div>
    </div>

    <div class="flex w-full gap-1.5 rounded-xl border border-white/10 bg-black/20 p-1">
      <button
        v-for="preset in presets"
        :key="preset.label"
        class="flex-1 rounded-lg px-3 py-1.5 text-xs transition disabled:opacity-30"
        :class="isPresetActive(preset) ? 'bg-calm/15 text-calm' : 'text-slate-400 hover:text-slate-200'"
        :disabled="!canSwitchMode"
        @click="timer.setMode(preset.mode, preset.minutes)"
      >
        {{ preset.label }}{{ preset.mode === 'pomodoro' ? ' 分钟' : '' }}
      </button>
    </div>

    <div class="flex w-full flex-col gap-2">
      <button v-if="!timer.isActive" class="btn-primary w-full" @click="$emit('start')">
        <AppIcon name="play" :size="15" />
        开始专注
      </button>
      <button v-if="timer.status === 'running'" class="btn-ghost w-full" @click="$emit('pause')">
        <AppIcon name="pause" :size="15" />
        暂停
      </button>
      <button v-if="timer.status === 'paused'" class="btn-primary w-full" @click="$emit('resume')">
        <AppIcon name="play" :size="15" />
        继续
      </button>
      <button v-if="timer.isActive" class="btn-danger w-full" @click="$emit('end')">
        <AppIcon name="stop" :size="15" />
        结束本次
      </button>
    </div>

    <p v-if="timer.lastMessage" class="text-center text-xs text-calm">{{ timer.lastMessage }}</p>
    <p v-if="timer.error" class="text-center text-xs text-rose-300">{{ timer.error }}</p>
    <p class="text-center text-[11px] leading-relaxed text-slate-500">
      计时跑在 Web Worker 里，切标签页也不会停；最终时长以服务端记录为准。
    </p>
  </div>
</template>
