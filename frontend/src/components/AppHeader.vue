<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppIcon from './AppIcon.vue'
import WallpaperPicker from './WallpaperPicker.vue'
import { NAV_PAGES } from '../utils/nav'
import { useUserStore } from '../stores/user'
import { formatDuration } from '../utils/format'

const user = useUserStore()
const route = useRoute()
const router = useRouter()

const initial = computed(() => (user.displayName || '?').slice(0, 1).toUpperCase())
// 房间详情页也属于"自习室"这个导航项
const activeName = computed(() => (route.name === 'room-detail' ? 'rooms' : route.name))

function isActive(name) {
  return activeName.value === name
}

function logout() {
  user.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <header class="sticky top-0 z-30 border-b border-white/10 bg-[#070b12]/70 backdrop-blur-xl">
    <div class="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3 sm:gap-5">
      <RouterLink to="/rooms" class="group flex items-center gap-2.5">
        <span
          class="flex h-9 w-9 items-center justify-center rounded-xl text-ink"
          style="background-image: linear-gradient(135deg, #7ff5df, #38bdf8)"
        >
          <AppIcon name="bolt" :size="18" />
        </span>
        <span class="hidden flex-col leading-tight sm:flex">
          <span class="text-sm font-semibold tracking-tight text-slate-50">线上自习室</span>
          <span class="text-[10px] text-slate-500">一起专注 · 记录 · 陪伴</span>
        </span>
      </RouterLink>

      <nav class="no-scrollbar flex flex-1 items-center gap-1 overflow-x-auto">
        <RouterLink
          v-for="page in NAV_PAGES"
          :key="page.name"
          :to="{ name: page.name }"
          class="flex shrink-0 items-center gap-1.5 rounded-xl px-3 py-2 text-sm transition"
          :class="
            isActive(page.name)
              ? 'bg-calm/10 text-calm shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]'
              : 'text-slate-400 hover:bg-white/[0.05] hover:text-slate-100'
          "
        >
          <AppIcon :name="page.icon" :size="16" />
          <span>{{ page.label }}</span>
        </RouterLink>
      </nav>

      <div class="flex shrink-0 items-center gap-2">
        <WallpaperPicker />

        <div
          v-if="user.profile"
          class="hidden items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.04] px-2.5 py-1.5 sm:flex"
        >
          <span
            class="flex h-7 w-7 items-center justify-center rounded-lg bg-white/10 text-xs font-semibold text-calm"
          >
            {{ initial }}
          </span>
          <span class="flex flex-col leading-tight">
            <span class="max-w-[8rem] truncate text-xs text-slate-200">{{ user.displayName }}</span>
            <span class="num text-[10px] text-slate-500">
              累计 {{ formatDuration(user.profile.total_duration) }}
            </span>
          </span>
        </div>

        <button class="btn-icon" title="退出登录" @click="logout">
          <AppIcon name="logout" :size="17" />
        </button>
      </div>
    </div>
  </header>
</template>
