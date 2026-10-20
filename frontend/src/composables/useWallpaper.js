import { computed, ref, watch } from 'vue'

const STORAGE_KEY = 'studyroom_wallpaper'
const CUSTOM_KEY = 'studyroom_wallpapers_custom'
const DIM_KEY = 'studyroom_wallpaper_dim'
const MAX_CUSTOM = 6
const MAX_IMAGE_CHARS = 2_600_000 // 约 2MB 的 base64，再多 localStorage 就存不下了
let idSeed = 0

/** 只用时间戳会在"同一毫秒连加几张"时撞 id，撞了就变成删一张删一串，所以再带个序号 */
function nextId() {
  idSeed += 1
  return 'w' + Date.now().toString(36) + idSeed.toString(36)
}

/**
 * 内置壁纸全部用 CSS 渐变 + 噪点生成，不依赖任何图片文件：
 * 不增加体积、不必等加载、任何分辨率都不糊。
 * 想用真实照片，直接在页面右上角的壁纸面板里加图片（链接或本地上传）。
 */
export const WALLPAPERS = [
  {
    key: 'auto',
    label: '自动',
    desc: '按当前时间自动换',
    css: 'linear-gradient(180deg, #070b14, #0a1020 55%, #070a12)',
    orbs: ['rgba(56,189,248,.30)', 'rgba(94,234,212,.24)', 'rgba(167,139,250,.26)'],
  },
  {
    key: 'midnight',
    label: '深夜',
    desc: '深蓝夜色，适合晚上',
    css: 'radial-gradient(1100px 700px at 12% -10%, rgba(56,110,255,.30), transparent 60%), radial-gradient(900px 600px at 92% 6%, rgba(139,92,246,.24), transparent 64%), radial-gradient(800px 700px at 45% 118%, rgba(13,148,136,.20), transparent 62%), linear-gradient(180deg, #070b14 0%, #0a1020 52%, #06090f 100%)',
    orbs: ['rgba(59,130,246,.34)', 'rgba(139,92,246,.28)', 'rgba(13,148,136,.22)'],
  },
  {
    key: 'aurora',
    label: '极光',
    desc: '青紫流动，最亮眼',
    css: 'radial-gradient(900px 620px at 8% 18%, rgba(45,212,191,.36), transparent 60%), radial-gradient(1000px 700px at 88% 12%, rgba(167,139,250,.32), transparent 62%), radial-gradient(760px 560px at 62% 96%, rgba(56,189,248,.24), transparent 60%), linear-gradient(180deg, #05080f 0%, #08131b 55%, #05080f 100%)',
    orbs: ['rgba(45,212,191,.40)', 'rgba(167,139,250,.34)', 'rgba(56,189,248,.30)'],
  },
  {
    key: 'lamp',
    label: '暖灯',
    desc: '台下暖光，适合深夜读书',
    css: 'radial-gradient(820px 620px at 18% 108%, rgba(251,191,36,.30), transparent 62%), radial-gradient(900px 520px at 86% -6%, rgba(244,114,182,.16), transparent 62%), linear-gradient(180deg, #0e0a07 0%, #15100b 55%, #0b0806 100%)',
    orbs: ['rgba(251,191,36,.32)', 'rgba(244,114,182,.20)', 'rgba(249,115,22,.22)'],
  },
  {
    key: 'forest',
    label: '森林',
    desc: '深绿静谧，护眼',
    css: 'radial-gradient(900px 620px at 82% -4%, rgba(34,197,94,.24), transparent 60%), radial-gradient(820px 720px at 8% 92%, rgba(16,185,129,.22), transparent 62%), linear-gradient(180deg, #050c0a 0%, #07130f 55%, #040908 100%)',
    orbs: ['rgba(34,197,94,.26)', 'rgba(16,185,129,.24)', 'rgba(45,212,191,.18)'],
  },
  {
    key: 'sakura',
    label: '樱雾',
    desc: '灰紫粉，柔和',
    css: 'radial-gradient(900px 620px at 14% 8%, rgba(244,114,182,.22), transparent 62%), radial-gradient(820px 620px at 88% 88%, rgba(129,140,248,.22), transparent 60%), linear-gradient(180deg, #0c0810 0%, #130d18 55%, #0a070d 100%)',
    orbs: ['rgba(244,114,182,.24)', 'rgba(129,140,248,.24)', 'rgba(251,191,36,.14)'],
  },
  {
    key: 'ink',
    label: '纯墨',
    desc: '极简深灰，长时间看不累',
    css: 'radial-gradient(1000px 700px at 50% -18%, rgba(148,163,184,.12), transparent 66%), linear-gradient(180deg, #06080c 0%, #090d14 58%, #06080c 100%)',
    orbs: ['rgba(148,163,184,.14)', 'rgba(94,234,212,.14)', 'rgba(100,116,139,.16)'],
  },
]

const FALLBACK = WALLPAPERS[0]

export function resolveAuto(hour = new Date().getHours()) {
  if (hour < 6) return 'midnight'
  if (hour < 9) return 'forest'
  if (hour < 17) return 'ink'
  if (hour < 20) return 'lamp'
  return 'aurora'
}

const canStore = typeof localStorage !== 'undefined'

function readRaw(key) {
  if (!canStore) return null
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function readList() {
  try {
    const parsed = JSON.parse(readRaw(CUSTOM_KEY) || '[]')
    if (!Array.isArray(parsed)) return []
    return parsed.filter((item) => item && item.id && typeof item.url === 'string')
  } catch {
    return []
  }
}

function readDim() {
  const value = Number(readRaw(DIM_KEY))
  return Number.isFinite(value) && value >= 0 && value <= 0.85 ? value : 0.35
}

const storedSelected = readRaw(STORAGE_KEY) || 'auto'
const customs = ref(readList())
const dim = ref(readDim())
const selected = ref(
  WALLPAPERS.some((item) => item.key === storedSelected) ||
    (storedSelected.startsWith('custom:') && customs.value.some((item) => 'custom:' + item.id === storedSelected))
    ? storedSelected
    : 'auto',
)
const storageError = ref('')

function persist(key, value) {
  if (!canStore) return
  try {
    localStorage.setItem(key, value)
    storageError.value = ''
  } catch {
    storageError.value = '浏览器存不下了：换小一点的图片，或者改用图片链接。'
  }
}

const resolvedKey = computed(() => (selected.value === 'auto' ? resolveAuto() : selected.value))

const currentCustom = computed(() =>
  selected.value.startsWith('custom:')
    ? customs.value.find((item) => 'custom:' + item.id === selected.value) || null
    : null,
)

const current = computed(() => {
  if (selected.value.startsWith('custom:')) {
    const item = currentCustom.value
    if (item) {
      return {
        key: selected.value,
        label: item.name,
        desc: '我自己的图片',
        css: 'linear-gradient(180deg, #05070c, #080c14)',
        orbs: [],
        image: item.url,
      }
    }
  }
  return WALLPAPERS.find((item) => item.key === resolvedKey.value) || FALLBACK
})

const label = computed(() =>
  selected.value === 'auto' ? '自动 · ' + current.value.label : current.value.label,
)

watch(selected, (value) => persist(STORAGE_KEY, value))
watch(customs, (value) => persist(CUSTOM_KEY, JSON.stringify(value)), { deep: true })
watch(dim, (value) => persist(DIM_KEY, String(value)))

function select(key) {
  selected.value = key
}

/** 加一张自己的图片；url 可以是图片链接，也可以是本地上传后转的 base64 */
function addCustom(url, name = '我的壁纸') {
  const clean = String(url || '').trim().replace(/["\n\r]/g, '')
  if (!clean) return { ok: false, error: '图片地址是空的' }
  if (clean.length > MAX_IMAGE_CHARS) return { ok: false, error: '图片太大了，请压缩后再上传，或改用图片链接。' }
  // 同一个地址再加一次就直接选中原来那张，不重复占位
  const existing = customs.value.find((item) => item.url === clean)
  if (existing) {
    selected.value = 'custom:' + existing.id
    return { ok: true }
  }
  if (customs.value.length >= MAX_CUSTOM) return { ok: false, error: '最多存 ' + MAX_CUSTOM + ' 张，先删掉一张吧。' }

  const id = nextId()
  customs.value = customs.value.concat([{ id, name: name.slice(0, 24) || '我的壁纸', url: clean }])
  if (storageError.value) {
    customs.value = customs.value.filter((item) => item.id !== id)
    return { ok: false, error: storageError.value }
  }
  selected.value = 'custom:' + id
  return { ok: true }
}

function removeCustom(id) {
  customs.value = customs.value.filter((item) => item.id !== id)
  if (selected.value === 'custom:' + id) selected.value = 'auto'
}

export function useWallpaper() {
  return {
    wallpapers: WALLPAPERS,
    customs,
    dim,
    selected,
    current,
    resolvedKey,
    label,
    storageError,
    maxCustom: MAX_CUSTOM,
    select,
    addCustom,
    removeCustom,
    setDim: (value) => {
      dim.value = Math.min(0.85, Math.max(0, Number(value) || 0))
    },
  }
}
