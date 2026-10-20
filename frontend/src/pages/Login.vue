<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppIcon from '../components/AppIcon.vue'
import { useUserStore } from '../stores/user'

const user = useUserStore()
const route = useRoute()
const router = useRouter()

const tab = ref('login')
const form = ref({ username: '', password: '', nickname: '' })
const error = ref('')
const loading = ref(false)

const tabs = [
  { key: 'login', label: '登录' },
  { key: 'register', label: '注册' },
]

const highlights = [
  { icon: 'users', text: '虚拟座位，看得见谁在专注' },
  { icon: 'clock', text: '番茄钟计时，切后台也不会停' },
  { icon: 'chart', text: '热力图与榜单，进度有迹可循' },
]

async function submit() {
  error.value = ''
  loading.value = true
  try {
    if (tab.value === 'login') {
      await user.login({ username: form.value.username, password: form.value.password })
    } else {
      await user.register({
        username: form.value.username,
        password: form.value.password,
        nickname: form.value.nickname || undefined,
      })
    }
    const redirect = route.query.redirect
    router.push(typeof redirect === 'string' && redirect ? redirect : { name: 'rooms' })
  } catch (err) {
    error.value = err.message || '操作失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-[calc(100vh-6rem)] items-center justify-center">
    <div class="grid w-full max-w-4xl items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
      <div class="hidden flex-col gap-6 lg:flex">
        <div>
          <span
            class="flex h-14 w-14 items-center justify-center rounded-2xl text-ink"
            style="background-image: linear-gradient(135deg, #7ff5df, #38bdf8)"
          >
            <AppIcon name="bolt" :size="26" />
          </span>
          <h1 class="mt-5 text-3xl font-semibold tracking-tight text-slate-50">
            有人陪着，<span class="text-calm glow-text">更容易坐得住</span>
          </h1>
          <p class="mt-3 max-w-md text-sm leading-relaxed text-slate-400">
            线上虚拟自习室：进房间占个座位、开番茄钟、记录时长，再让 AI 帮你复盘和拆计划。
          </p>
        </div>

        <ul class="flex flex-col gap-3">
          <li
            v-for="item in highlights"
            :key="item.text"
            class="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-300"
          >
            <span class="flex h-8 w-8 items-center justify-center rounded-xl bg-calm/10 text-calm">
              <AppIcon :name="item.icon" :size="16" />
            </span>
            {{ item.text }}
          </li>
        </ul>
      </div>

      <div class="mx-auto w-full max-w-md">
        <div class="mb-6 flex flex-col items-center text-center lg:hidden">
          <span
            class="flex h-12 w-12 items-center justify-center rounded-2xl text-ink"
            style="background-image: linear-gradient(135deg, #7ff5df, #38bdf8)"
          >
            <AppIcon name="bolt" :size="22" />
          </span>
          <h1 class="mt-3 text-xl font-semibold tracking-tight text-slate-50">线上自习室</h1>
        </div>

        <div class="card card-hover p-6">
          <div class="flex gap-1 rounded-xl border border-white/10 bg-black/25 p-1 text-sm">
            <button
              v-for="item in tabs"
              :key="item.key"
              class="flex-1 rounded-lg py-2 transition"
              :class="
                tab === item.key
                  ? 'bg-calm/15 text-calm shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]'
                  : 'text-slate-400 hover:text-slate-200'
              "
              @click="tab = item.key"
            >
              {{ item.label }}
            </button>
          </div>

          <form class="mt-5 flex flex-col gap-4" @submit.prevent="submit">
            <div>
              <label class="label">用户名</label>
              <input
                v-model="form.username"
                class="input"
                autocomplete="username"
                placeholder="3-32 位，字母 / 数字 / 下划线 / 中文"
              />
            </div>
            <div v-if="tab === 'register'">
              <label class="label">昵称（可选）</label>
              <input v-model="form.nickname" class="input" placeholder="房间里显示的名字" />
            </div>
            <div>
              <label class="label">密码</label>
              <input
                v-model="form.password"
                type="password"
                class="input"
                autocomplete="current-password"
                placeholder="至少 6 位"
              />
            </div>

            <button type="submit" class="btn-primary mt-1 w-full py-2.5" :disabled="loading">
              <AppIcon :name="tab === 'login' ? 'door' : 'sparkles'" :size="16" />
              {{ loading ? '处理中…' : tab === 'login' ? '进入自习室' : '注册并进入' }}
            </button>
            <p
              v-if="error"
              class="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200"
            >
              {{ error }}
            </p>
          </form>
        </div>

        <p class="mt-5 text-center text-[11px] leading-relaxed text-slate-600">
          专注时长由服务端记录，换设备、切标签页都不会丢。
        </p>
      </div>
    </div>
  </div>
</template>
