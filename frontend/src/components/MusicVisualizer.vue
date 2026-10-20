<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  analyser: { type: Object, default: null },
  playing: { type: Boolean, default: false },
  bars: { type: Number, default: 44 },
  height: { type: Number, default: 84 },
})

const host = ref(null)
const canvas = ref(null)

let ctx = null
let raf = 0
let observer = null
let data = null

function resize() {
  const el = canvas.value
  if (!el) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const width = Math.max(1, Math.floor(el.clientWidth * dpr))
  const height = Math.max(1, Math.floor(el.clientHeight * dpr))
  if (el.width !== width || el.height !== height) {
    el.width = width
    el.height = height
  }
}

function draw(now) {
  raf = requestAnimationFrame(draw)
  const el = canvas.value
  if (!el) return
  if (!el.clientWidth || !el.clientHeight) return
  resize()
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const width = el.width / dpr
  const height = el.height / dpr
  if (!ctx) ctx = el.getContext('2d')
  if (!ctx) return
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, width, height)

  const count = Math.max(18, Math.min(props.bars, Math.floor(width / 5)))
  const gap = 2
  const barWidth = Math.max(1.4, (width - gap * (count - 1)) / count)
  const live = Boolean(props.analyser && props.playing)

  if (live) {
    if (!data || data.length !== props.analyser.frequencyBinCount) {
      data = new Uint8Array(props.analyser.frequencyBinCount)
    }
    props.analyser.getByteFrequencyData(data)
  }

  const gradient = ctx.createLinearGradient(0, 0, width, 0)
  gradient.addColorStop(0, '#5eead4')
  gradient.addColorStop(0.55, '#38bdf8')
  gradient.addColorStop(1, '#a78bfa')
  ctx.fillStyle = gradient
  ctx.shadowColor = 'rgba(56, 189, 248, 0.55)'
  ctx.shadowBlur = live ? 10 : 0

  const bar = (x, y, width, height, radius) => {
    if (typeof ctx.roundRect === 'function') {
      ctx.beginPath()
      ctx.roundRect(x, y, width, height, radius)
      ctx.fill()
    } else {
      ctx.fillRect(x, y, width, height)
    }
  }

  const usable = live ? Math.max(8, Math.floor(data.length * 0.72)) : 1
  const base = height - 6

  for (let i = 0; i < count; i += 1) {
    let value
    if (live) {
      const index = Math.min(usable - 1, Math.floor(Math.pow(i / (count - 1), 1.65) * usable))
      value = data[index] / 255
      value = Math.pow(value, 1.25)
    } else {
      const wave = Math.sin(now * 0.0014 + i * 0.46) * 0.5 + 0.5
      value = 0.04 + wave * 0.08
    }
    const barHeight = Math.max(2, value * (height - 14))
    const x = i * (barWidth + gap)
    ctx.globalAlpha = live ? 0.92 : 0.5
    bar(x, base - barHeight, barWidth, barHeight, Math.min(barWidth / 2, 3))

    ctx.globalAlpha = live ? 0.18 : 0.08
    bar(x, base + 1, barWidth, barHeight * 0.28, Math.min(barWidth / 2, 3))
  }

  ctx.globalAlpha = 1
  ctx.shadowBlur = 0
  ctx.strokeStyle = 'rgba(148, 163, 184, 0.18)'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(0, base + 0.5)
  ctx.lineTo(width, base + 0.5)
  ctx.stroke()
}

onMounted(() => {
  if ('ResizeObserver' in window && host.value) {
    observer = new ResizeObserver(resize)
    observer.observe(host.value)
  }
  raf = requestAnimationFrame(draw)
})

watch(
  () => props.analyser,
  () => {
    data = null
  },
)

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  if (observer) observer.disconnect()
  ctx = null
  data = null
})
</script>

<template>
  <div
    ref="host"
    class="relative w-full overflow-hidden rounded-xl border border-white/10 bg-black/30"
    :style="{ height: height + 'px' }"
  >
    <canvas ref="canvas" class="absolute inset-0 h-full w-full" />
    <span
      v-if="!playing"
      class="pointer-events-none absolute inset-0 flex items-center justify-center text-[10px] tracking-widest text-slate-500"
    >
      频谱待机
    </span>
  </div>
</template>
