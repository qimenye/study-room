<script setup>
import { computed, markRaw, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'

import AppIcon from './AppIcon.vue'
import MusicVisualizer from './MusicVisualizer.vue'
import NeteaseLogin from './NeteaseLogin.vue'
import { musicApi } from '../api/music'
import { formatClock } from '../utils/format'

const QUICK = ['雨声', '钢琴', 'Lo-fi', '森林', '白噪音']

const audioEl = ref(null)
const analyser = shallowRef(null)
const query = ref('')
const results = ref([])
const searched = ref(false)
const loading = ref(false)
const error = ref('')
const current = ref(null)
const playing = ref(false)
const volume = ref(0.7)
const elapsed = ref(0)
const duration = ref(0)

const settings = ref(null)
const settingsOpen = ref(false)

let ctx = null
let source = null
let gain = null
let analyserNode = null

const hasCookie = computed(() => Boolean(settings.value?.has_cookie))
const statusText = computed(() => {
  if (!hasCookie.value) return '未登录 · 扫码或用手机号登录'
  return '已登录 · ' + (settings.value?.nickname || settings.value?.cookie_masked || '网易云')
})

function ensureAudio() {
  if (!audioEl.value) return
  if (!ctx) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    ctx = new AudioCtx()
    source = ctx.createMediaElementSource(audioEl.value)
    analyserNode = ctx.createAnalyser()
    analyserNode.fftSize = 256
    analyserNode.smoothingTimeConstant = 0.84
    gain = ctx.createGain()
    gain.gain.value = volume.value
    source.connect(analyserNode)
    analyserNode.connect(gain)
    gain.connect(ctx.destination)
    analyser.value = markRaw(analyserNode)
    audioEl.value.volume = 1
  }
  if (ctx.state === 'suspended') ctx.resume()
}

function formatTime(seconds) {
  return formatClock(seconds || 0)
}

async function playSong(song) {
  if (!song || !song.id || !audioEl.value) return
  error.value = ''
  ensureAudio()
  if (current.value?.id === song.id && !audioEl.value.paused) {
    audioEl.value.pause()
    return
  }
  if (current.value?.id !== song.id) {
    current.value = song
    elapsed.value = 0
    duration.value = song.duration || 0
    audioEl.value.src = musicApi.streamUrl(song.id)
    audioEl.value.load()
  }
  try {
    await audioEl.value.play()
  } catch (err) {
    if (err && err.name === 'AbortError') return
    playing.value = false
    error.value = '浏览器没能开始播放，再点一次试试。'
  }
}

function togglePlay() {
  if (!current.value || !audioEl.value) return
  if (audioEl.value.paused) {
    ensureAudio()
    audioEl.value.play().catch(() => {
      playing.value = false
      error.value = '浏览器拦截了播放，再点一次播放键。'
    })
  } else {
    audioEl.value.pause()
  }
}

function onPlay() {
  playing.value = true
  error.value = ''
}

function onPause() {
  playing.value = false
}

function onEnded() {
  playing.value = false
  const index = results.value.findIndex((item) => item.id === current.value?.id)
  if (index >= 0 && index + 1 < results.value.length) {
    playSong(results.value[index + 1])
  }
}

function onTimeUpdate() {
  if (!audioEl.value) return
  elapsed.value = audioEl.value.currentTime || 0
  if (Number.isFinite(audioEl.value.duration) && audioEl.value.duration > 0) {
    duration.value = audioEl.value.duration
  }
}

function onLoaded() {
  if (audioEl.value && Number.isFinite(audioEl.value.duration)) {
    duration.value = audioEl.value.duration
  }
}

function onError() {
  playing.value = false
  error.value = '这首歌暂时放不了：可能要登录、要 VIP 或没有版权，换一首试试。'
}

function seek(event) {
  const value = Number(event.target.value)
  if (!audioEl.value || !Number.isFinite(value)) return
  audioEl.value.currentTime = value
  elapsed.value = value
}

async function runSearch(keyword) {
  const text = (keyword ?? query.value).trim()
  if (!text || loading.value) return
  query.value = text
  loading.value = true
  error.value = ''
  searched.value = true
  try {
    const data = await musicApi.search(text, 30, 0)
    results.value = data.songs || []
  } catch (err) {
    results.value = []
    error.value = err.status === 401 ? '登录过期了，刷新页面重新登录。' : err.message || '搜索失败'
  } finally {
    loading.value = false
  }
}

async function loadSettings() {
  try {
    settings.value = await musicApi.settings()
  } catch {
    // 设置读不到不影响搜索
  }
}

function onSettingsChanged(next) {
  settings.value = next
}

watch(volume, (value) => {
  if (!gain || !ctx) return
  gain.gain.setTargetAtTime(value, ctx.currentTime, 0.08)
})

onMounted(loadSettings)

onBeforeUnmount(() => {
  if (audioEl.value) {
    audioEl.value.pause()
    audioEl.value.removeAttribute('src')
  }
  if (source) source.disconnect()
  if (analyserNode) analyserNode.disconnect()
  if (gain) gain.disconnect()
  if (ctx) ctx.close().catch(() => {})
  ctx = null
  source = null
  analyserNode = null
  gain = null
})
</script>

<template>
  <div class="flex flex-col gap-3">
    <audio
      ref="audioEl"
      class="hidden"
      crossorigin="anonymous"
      preload="none"
      @play="onPlay"
      @pause="onPause"
      @ended="onEnded"
      @timeupdate="onTimeUpdate"
      @loadedmetadata="onLoaded"
      @error="onError"
    />

    <div class="flex items-center justify-between gap-2">
      <span class="flex min-w-0 items-center gap-1.5 text-[11px] text-slate-500">
        <span
          class="h-1.5 w-1.5 shrink-0 rounded-full"
          :class="hasCookie ? 'bg-calm' : 'bg-slate-600'"
        />
        <span class="truncate">{{ statusText }}</span>
      </span>
      <button
        class="inline-flex shrink-0 items-center gap-1 text-[11px] text-slate-400 transition hover:text-calm"
        @click="settingsOpen = !settingsOpen"
      >
        <AppIcon name="key" :size="13" />
        {{ hasCookie ? '账号' : '网易云登录' }}
        <AppIcon :name="settingsOpen ? 'chevronUp' : 'chevronDown'" :size="13" />
      </button>
    </div>

    <NeteaseLogin
      v-if="settingsOpen"
      :state="settings"
      @changed="onSettingsChanged"
      @close="settingsOpen = false"
    />

    <form class="flex gap-2" @submit.prevent="runSearch()">
      <input
        v-model="query"
        class="input"
        maxlength="60"
        placeholder="搜歌名 / 歌手，例如「雨声」"
        @keyup.enter.prevent="runSearch()"
      />
      <button class="btn-primary shrink-0 px-3" :disabled="loading" title="搜索">
        <AppIcon name="search" :size="16" />
      </button>
    </form>

    <div class="flex flex-wrap gap-1.5">
      <button
        v-for="word in QUICK"
        :key="word"
        class="tag transition hover:border-calm/40 hover:text-calm"
        @click="runSearch(word)"
      >
        {{ word }}
      </button>
    </div>

    <p v-if="loading" class="px-1 text-[11px] text-slate-500">正在搜网易云…</p>
    <div
      v-else-if="results.length"
      class="max-h-56 overflow-y-auto rounded-xl border border-white/10 bg-black/20"
    >
      <button
        v-for="song in results"
        :key="song.id"
        :data-song-id="song.id"
        class="flex w-full items-center gap-2.5 border-b border-white/[0.06] px-2.5 py-2 text-left transition last:border-0 hover:bg-white/[0.045]"
        @click="playSong(song)"
      >
        <img
          v-if="song.cover"
          :src="song.cover"
          alt=""
          class="h-9 w-9 shrink-0 rounded-lg object-cover"
          loading="lazy"
          referrerpolicy="no-referrer"
        />
        <span v-else class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/5">
          <AppIcon name="music" :size="15" class="text-slate-500" />
        </span>
        <span class="min-w-0 flex-1">
          <span class="flex items-center gap-1.5">
            <span
              class="truncate text-xs"
              :class="current?.id === song.id ? 'text-calm' : 'text-slate-200'"
            >
              {{ song.name }}
            </span>
            <span v-if="song.vip" class="tag shrink-0 border-amber-400/30 text-amber-300/90">VIP</span>
          </span>
          <span class="mt-0.5 block truncate text-[10px] text-slate-500">
            {{ song.artists }}<template v-if="song.album"> · {{ song.album }}</template>
          </span>
        </span>
        <span class="num shrink-0 text-[10px] text-slate-500">{{ formatTime(song.duration) }}</span>
        <AppIcon
          :name="current?.id === song.id && playing ? 'pause' : 'play'"
          :size="15"
          class="shrink-0"
          :class="current?.id === song.id ? 'text-calm' : 'text-slate-500'"
        />
      </button>
    </div>
    <p v-else-if="searched && !error" class="px-1 text-[11px] text-slate-500">
      没搜到，换个关键词试试。
    </p>
    <p
      v-if="error"
      class="rounded-xl border border-rose-500/30 bg-rose-500/[0.08] px-3 py-2 text-[11px] leading-relaxed text-rose-200"
    >
      {{ error }}
    </p>

    <div v-if="current" class="rounded-xl border border-calm/25 bg-calm/[0.05] p-3">
      <div class="flex items-center gap-2.5">
        <img
          v-if="current.cover"
          :src="current.cover"
          alt=""
          class="h-11 w-11 shrink-0 rounded-lg object-cover"
          referrerpolicy="no-referrer"
        />
        <span v-else class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-white/5">
          <AppIcon name="music" :size="18" class="text-calm" />
        </span>
        <span class="min-w-0 flex-1">
          <span class="block truncate text-xs text-slate-100">{{ current.name }}</span>
          <span class="mt-0.5 block truncate text-[10px] text-slate-500">{{ current.artists }}</span>
        </span>
        <button class="btn-icon h-9 w-9 shrink-0" :title="playing ? '暂停' : '播放'" @click="togglePlay">
          <AppIcon :name="playing ? 'pause' : 'play'" :size="16" />
        </button>
      </div>

      <MusicVisualizer class="mt-2.5" :analyser="analyser" :playing="playing" :height="78" />

      <div class="mt-2 flex items-center gap-2 text-[10px] text-slate-500">
        <span class="num">{{ formatTime(elapsed) }}</span>
        <input
          type="range"
          min="0"
          :max="duration || 0"
          step="0.1"
          :value="elapsed"
          class="flex-1"
          :disabled="!duration"
          @input="seek"
        />
        <span class="num">{{ formatTime(duration) }}</span>
      </div>
      <label class="mt-2 flex items-center gap-2 text-[10px] text-slate-500">
        <AppIcon name="volume" :size="14" />
        <input v-model.number="volume" type="range" min="0" max="1" step="0.05" class="flex-1" />
        <span class="num w-6 text-right">{{ Math.round(volume * 100) }}</span>
      </label>
    </div>
    <div v-else class="rounded-xl border border-dashed border-white/10 px-3 py-4 text-center">
      <AppIcon name="music" :size="22" class="mx-auto text-slate-600" />
      <p class="mt-1 text-[11px] text-slate-500">搜一首歌，播放后频谱会跟着动。</p>
    </div>

    <p class="text-[10px] leading-relaxed text-slate-500">
      走网易云网页端接口（非官方），接口变化或版权限制都可能导致某首歌放不了；登录自己的网易云账号成功率更高。
    </p>
  </div>
</template>
