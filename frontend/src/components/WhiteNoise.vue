<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import AppIcon from './AppIcon.vue'
import MusicPlayer from './MusicPlayer.vue'

const props = defineProps({
  suggested: { type: String, default: '' },
})

const SOUNDS = [
  { key: 'rain', label: '雨声', icon: 'rain', desc: '白噪音 + 低通' },
  { key: 'cafe', label: '咖啡馆', icon: 'coffee', desc: '粉噪音 + 带通' },
  { key: 'library', label: '图书馆', icon: 'book', desc: '极轻环境底噪' },
  { key: 'waves', label: '海浪', icon: 'waves', desc: '布朗噪音 + 起伏' },
  { key: 'brown', label: '深噪', icon: 'waveform', desc: '无调性，最易忽略' },
]

const playing = ref(false)
const current = ref('')
const volume = ref(0.5)
const hint = ref('')
const tab = ref('noise')

let ctx = null
let sourceNode = null
let filterNode = null
let gainNode = null
let lfoNode = null
let lfoGainNode = null

const activeLabel = computed(() => SOUNDS.find((item) => item.key === current.value)?.label || '')

function makeNoiseBuffer(context, kind) {
  const seconds = 4
  const length = Math.floor(context.sampleRate * seconds)
  const buffer = context.createBuffer(1, length, context.sampleRate)
  const data = buffer.getChannelData(0)
  let brown = 0
  let b0 = 0
  let b1 = 0
  let b2 = 0
  let b3 = 0
  let b4 = 0
  let b5 = 0
  let b6 = 0
  for (let i = 0; i < length; i += 1) {
    const white = Math.random() * 2 - 1
    if (kind === 'brown') {
      brown = (brown + 0.02 * white) / 1.02
      data[i] = brown * 3.2
    } else if (kind === 'library' || kind === 'cafe') {
      b0 = 0.99886 * b0 + white * 0.0555179
      b1 = 0.99332 * b1 + white * 0.0750759
      b2 = 0.969 * b2 + white * 0.153852
      b3 = 0.8665 * b3 + white * 0.3104856
      b4 = 0.55 * b4 + white * 0.5329522
      b5 = -0.7616 * b5 - white * 0.016898
      const pink = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.11
      b6 = white * 0.115926
      data[i] = kind === 'cafe' ? pink * 2.2 : pink * 1.6
    } else {
      data[i] = white * 0.55
    }
  }
  return buffer
}

function ensureContext() {
  if (!ctx) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    ctx = new AudioCtx()
  }
  if (ctx.state === 'suspended') ctx.resume()
  return ctx
}

function stop() {
  playing.value = false
  try {
    if (lfoNode) lfoNode.stop()
  } catch {
    // 忽略
  }
  try {
    if (sourceNode) sourceNode.stop()
  } catch {
    // 忽略
  }
  if (sourceNode) sourceNode.disconnect()
  if (filterNode) filterNode.disconnect()
  if (gainNode) gainNode.disconnect()
  sourceNode = null
  filterNode = null
  gainNode = null
  lfoNode = null
  lfoGainNode = null
}

function play(key) {
  const context = ensureContext()
  stop()

  sourceNode = context.createBufferSource()
  sourceNode.buffer = makeNoiseBuffer(context, key)
  sourceNode.loop = true

  filterNode = context.createBiquadFilter()
  gainNode = context.createGain()
  gainNode.gain.value = 0

  if (key === 'rain') {
    filterNode.type = 'lowpass'
    filterNode.frequency.value = 2200
    filterNode.Q.value = 0.6
  } else if (key === 'cafe') {
    filterNode.type = 'bandpass'
    filterNode.frequency.value = 700
    filterNode.Q.value = 0.7
  } else if (key === 'library') {
    filterNode.type = 'lowpass'
    filterNode.frequency.value = 900
    filterNode.Q.value = 0.5
  } else if (key === 'waves') {
    filterNode.type = 'lowpass'
    filterNode.frequency.value = 600
    filterNode.Q.value = 0.8
  } else {
    filterNode.type = 'lowpass'
    filterNode.frequency.value = 1200
    filterNode.Q.value = 0.4
  }

  sourceNode.connect(filterNode)
  filterNode.connect(gainNode)
  gainNode.connect(context.destination)

  if (key === 'waves') {
    lfoNode = context.createOscillator()
    lfoGainNode = context.createGain()
    lfoNode.frequency.value = 0.09
    lfoGainNode.gain.value = 0.28
    lfoNode.connect(lfoGainNode)
    lfoGainNode.connect(gainNode.gain)
    lfoNode.start()
  }

  const target = volume.value * (key === 'library' ? 0.5 : 0.8)
  gainNode.gain.setTargetAtTime(target, context.currentTime, 0.6)
  sourceNode.start()

  current.value = key
  playing.value = true
  hint.value = ''
}

function toggle(key) {
  if (playing.value && current.value === key) {
    stop()
    return
  }
  play(key)
}

watch(volume, (value) => {
  if (!gainNode || !ctx) return
  const scale = current.value === 'library' ? 0.5 : 0.8
  gainNode.gain.setTargetAtTime(value * scale, ctx.currentTime, 0.2)
})

watch(
  () => props.suggested,
  (value) => {
    if (!value) return
    const item = SOUNDS.find((sound) => sound.key === value)
    if (item) hint.value = '房间主题推荐：' + item.label
  },
  { immediate: true },
)

onBeforeUnmount(stop)
</script>

<template>
  <div class="card flex flex-col gap-4">
    <div class="flex items-center justify-between gap-2">
      <span class="flex items-center gap-1.5 text-sm text-slate-400">
        <AppIcon name="waveform" :size="15" />
        声音
      </span>
      <div class="flex shrink-0 rounded-lg border border-white/10 bg-black/20 p-0.5 text-[11px]">
        <button
          class="flex items-center gap-1 rounded-md px-2.5 py-1 transition"
          :class="tab === 'noise' ? 'bg-calm/15 text-calm' : 'text-slate-500 hover:text-slate-300'"
          @click="tab = 'noise'"
        >
          白噪音
        </button>
        <button
          class="flex items-center gap-1 rounded-md px-2.5 py-1 transition"
          :class="tab === 'music' ? 'bg-calm/15 text-calm' : 'text-slate-500 hover:text-slate-300'"
          @click="tab = 'music'"
        >
          <AppIcon name="music" :size="12" />
          网易云
        </button>
      </div>
    </div>

    <div v-show="tab === 'noise'" class="flex flex-col gap-4">
      <div class="flex items-center justify-between">
        <span class="text-[11px] text-slate-500">
          {{ playing ? '正在播放' : '选一个环境音' }}
        </span>
        <span v-if="playing" class="badge-live">
          <span class="h-1.5 w-1.5 animate-breathe rounded-full bg-calm" />
          {{ activeLabel }}
        </span>
      </div>

      <div class="grid grid-cols-2 gap-2">
        <button
          v-for="sound in SOUNDS"
          :key="sound.key"
          class="flex items-center gap-2 rounded-xl border px-3 py-2 text-left transition"
          :class="
            playing && current === sound.key
              ? 'border-calm/50 bg-calm/10 text-calm'
              : 'border-white/10 bg-white/[0.03] text-slate-300 hover:border-calm/35 hover:text-calm'
          "
          @click="toggle(sound.key)"
        >
          <AppIcon :name="sound.icon" :size="16" class="shrink-0" />
          <span class="min-w-0">
            <span class="block truncate text-xs">{{ sound.label }}</span>
            <span class="block truncate text-[10px] text-slate-500">{{ sound.desc }}</span>
          </span>
        </button>
      </div>

      <label class="flex items-center gap-3 text-xs text-slate-400">
        音量
        <input v-model.number="volume" type="range" min="0" max="1" step="0.05" class="flex-1" />
        <span class="num w-7 text-right">{{ Math.round(volume * 100) }}</span>
      </label>

      <p v-if="hint" class="text-[11px] text-calm">{{ hint }}</p>
      <p class="text-[11px] leading-relaxed text-slate-500">
        全部由 Web Audio 实时合成，不含任何音频文件——没有版权风险，也不增加体积。
      </p>
    </div>

    <div v-show="tab === 'music'">
      <MusicPlayer />
    </div>
  </div>
</template>
