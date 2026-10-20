<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

import AppIcon from './AppIcon.vue'
import { useWallpaper } from '../composables/useWallpaper'

const {
  wallpapers,
  customs,
  dim,
  selected,
  current,
  label,
  select,
  addCustom,
  removeCustom,
  setDim,
  storageError,
  maxCustom,
} = useWallpaper()

const open = ref(false)
const adding = ref(false)
const url = ref('')
const name = ref('')
const error = ref('')
const busy = ref(false)
const root = ref(null)
const fileInput = ref(null)

const MAX_UPLOAD = 6 * 1024 * 1024

function onDocumentClick(event) {
  if (root.value && !root.value.contains(event.target)) {
    open.value = false
    adding.value = false
  }
}

onMounted(() => document.addEventListener('click', onDocumentClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocumentClick))

function styleOf(item) {
  return item.url ? { backgroundImage: 'url("' + item.url + '")' } : { background: item.css }
}

/** 本地图片压到 1920px 宽再转 base64，否则 localStorage 放不下 */
async function shrink(file) {
  const dataUrl = await new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(new Error('读取图片失败'))
    reader.readAsDataURL(file)
  })
  if (file.type === 'image/svg+xml' || dataUrl.length < 900000) return dataUrl

  const image = await new Promise((resolve, reject) => {
    const el = new Image()
    el.onload = () => resolve(el)
    el.onerror = () => reject(new Error('这张图片解析不了，换一张试试'))
    el.src = dataUrl
  })
  const maxWidth = 1920
  if (image.width <= maxWidth) return dataUrl

  const scale = maxWidth / image.width
  const canvas = document.createElement('canvas')
  canvas.width = maxWidth
  canvas.height = Math.round(image.height * scale)
  canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height)
  return canvas.toDataURL('image/jpeg', 0.82)
}

function apply(result) {
  if (result.ok) {
    url.value = ''
    name.value = ''
    error.value = ''
    adding.value = false
    return true
  }
  error.value = result.error
  return false
}

function applyUrl() {
  const guess = (url.value.split('/').pop() || '').split('?')[0].replace(/\.[a-z0-9]+$/i, '')
  apply(addCustom(url.value, name.value || guess || '我的壁纸'))
}

async function onFile(event) {
  const file = event.target.files && event.target.files[0]
  event.target.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) {
    error.value = '只能选图片文件'
    return
  }
  if (file.size > MAX_UPLOAD) {
    error.value = '图片超过 6MB，先压缩一下再上传'
    return
  }
  busy.value = true
  error.value = ''
  try {
    const dataUrl = await shrink(file)
    apply(addCustom(dataUrl, name.value || file.name.replace(/\.[^.]+$/, '') || '本地图片'))
  } catch (err) {
    error.value = err.message || '处理图片失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div ref="root" class="relative">
    <button class="btn-icon" :title="'壁纸：' + label" @click="open = !open">
      <AppIcon name="palette" :size="18" />
    </button>

    <Transition name="page">
      <div
        v-if="open"
        data-scroll-lock
        class="absolute right-0 z-40 mt-2 max-h-[76vh] w-80 overflow-y-auto rounded-2xl border border-white/10 bg-[#0b1220]/95 p-3 backdrop-blur-xl"
        style="box-shadow: 0 30px 60px -30px rgba(0, 0, 0, 0.95)"
      >
        <div class="px-1 pb-2 text-[11px] uppercase tracking-widest text-slate-500">背景壁纸</div>

        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="item in wallpapers"
            :key="item.key"
            class="group flex flex-col gap-1 rounded-xl border p-1 transition"
            :class="
              selected === item.key
                ? 'border-calm/60 bg-calm/10'
                : 'border-white/10 hover:border-calm/40'
            "
            :title="item.desc"
            @click="select(item.key)"
          >
            <span class="relative block h-12 w-full overflow-hidden rounded-lg border border-white/10">
              <span class="absolute inset-0" :style="styleOf(item)" />
              <AppIcon
                v-if="selected === item.key"
                name="check"
                :size="13"
                class="absolute right-1 top-1 text-calm"
              />
            </span>
            <span class="truncate text-[11px]" :class="selected === item.key ? 'text-calm' : 'text-slate-400'">
              {{ item.label }}
            </span>
          </button>
        </div>

        <div class="mt-4 flex items-center justify-between px-1">
          <span class="text-[11px] uppercase tracking-widest text-slate-500">
            我的图片（{{ customs.length }}/{{ maxCustom }}）
          </span>
          <button
            class="text-[11px] text-slate-400 transition hover:text-calm"
            @click="adding = !adding"
          >
            {{ adding ? '收起' : '+ 添加' }}
          </button>
        </div>

        <div class="mt-2 grid grid-cols-3 gap-2">
          <div
            v-for="item in customs"
            :key="item.id"
            class="group relative flex flex-col gap-1 rounded-xl border p-1 transition"
            :class="
              selected === 'custom:' + item.id
                ? 'border-calm/60 bg-calm/10'
                : 'border-white/10 hover:border-calm/40'
            "
          >
            <button class="flex flex-col gap-1" @click="select('custom:' + item.id)">
              <span
                class="block h-12 w-full rounded-lg border border-white/10 bg-cover bg-center"
                :style="styleOf(item)"
              />
              <span
                class="truncate text-[11px]"
                :class="selected === 'custom:' + item.id ? 'text-calm' : 'text-slate-400'"
              >
                {{ item.name }}
              </span>
            </button>
            <button
              class="absolute -right-1 -top-1 hidden h-5 w-5 items-center justify-center rounded-full border border-white/15 bg-black/70 text-slate-300 transition hover:text-rose-300 group-hover:flex"
              title="删除这张"
              @click.stop="removeCustom(item.id)"
            >
              <AppIcon name="close" :size="11" />
            </button>
          </div>

          <button
            v-if="!customs.length"
            class="flex h-[3.9rem] flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-white/15 text-[11px] text-slate-500 transition hover:border-calm/40 hover:text-calm"
            @click="adding = true"
          >
            <AppIcon name="image" :size="16" />
            加图片
          </button>
        </div>

        <Transition name="page">
          <div v-if="adding" class="mt-2 flex flex-col gap-2 rounded-xl border border-white/10 bg-black/25 p-2">
            <input v-model="url" class="input text-xs" placeholder="粘贴图片链接 https://…" />
            <input v-model="name" class="input text-xs" placeholder="给它起个名字（可选）" />
            <div class="flex flex-wrap items-center gap-2">
              <button class="btn-primary px-3 py-1 text-xs" :disabled="!url" @click="applyUrl">
                用这个链接
              </button>
              <button class="btn-ghost px-3 py-1 text-xs" :disabled="busy" @click="fileInput.click()">
                <AppIcon name="upload" :size="14" />
                {{ busy ? '处理中…' : '上传本地图片' }}
              </button>
              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                class="hidden"
                @change="onFile"
              />
            </div>
            <p v-if="error || storageError" class="text-[11px] text-rose-300">
              {{ error || storageError }}
            </p>
            <p class="text-[11px] leading-relaxed text-slate-500">
              图片只存在你自己的浏览器里，不会上传到服务器。
            </p>
          </div>
        </Transition>

        <div v-if="current.image" class="mt-3 rounded-xl border border-white/10 bg-black/20 p-2.5">
          <div class="flex items-center justify-between text-[11px] text-slate-400">
            <span>遮罩强度（压暗图片，保证文字看得清）</span>
            <span class="num">{{ Math.round(dim * 100) }}%</span>
          </div>
          <input
            :value="dim"
            type="range"
            min="0"
            max="0.85"
            step="0.05"
            class="mt-2"
            @input="(event) => setDim(event.target.value)"
          />
        </div>

        <div class="mt-3 border-t border-white/10 px-1 pt-2 text-[11px] text-slate-500">
          当前：{{ label }}
          <span v-if="selected === 'auto'">（自动模式会按时间段切换）</span>
        </div>
      </div>
    </Transition>
  </div>
</template>
