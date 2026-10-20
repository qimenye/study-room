<script setup>
import { computed, onMounted, ref } from 'vue'

import AppIcon from '../components/AppIcon.vue'
import { rankingApi } from '../api/ranking'
import { useUserStore } from '../stores/user'
import { formatDuration } from '../utils/format'

const user = useUserStore()
const period = ref('today')
const items = ref([])
const loading = ref(false)

const periods = [
  { key: 'today', label: '今日榜' },
  { key: 'week', label: '本周榜' },
  { key: 'month', label: '本月榜' },
  { key: 'all', label: '总榜' },
]

const podium = computed(() => items.value.slice(0, 3))
const rest = computed(() => items.value.slice(3))

const RANK_STYLE = {
  1: 'border-warm/45 bg-warm/[0.07] text-warm',
  2: 'border-slate-300/30 bg-white/[0.05] text-slate-200',
  3: 'border-orange-400/30 bg-orange-400/[0.06] text-orange-300',
}

const isSelf = (item) => item.user_id === user.profile?.id

async function load() {
  loading.value = true
  try {
    items.value = await rankingApi.list(period.value, 50)
  } finally {
    loading.value = false
  }
}

async function change(value) {
  period.value = value
  await load()
}

onMounted(load)
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h2 class="page-title">排行榜</h2>
        <p class="mt-1 text-xs text-slate-500">按专注时长排名，只统计真实记录的时长。</p>
      </div>
      <div class="flex gap-1 rounded-xl border border-white/10 bg-black/20 p-1">
        <button
          v-for="item in periods"
          :key="item.key"
          class="rounded-lg px-3 py-1.5 text-xs transition"
          :class="
            period === item.key ? 'bg-calm/15 text-calm' : 'text-slate-400 hover:text-slate-200'
          "
          @click="change(item.key)"
        >
          {{ item.label }}
        </button>
      </div>
    </div>

    <p v-if="loading && !items.length" class="card py-10 text-center text-sm text-slate-500">
      加载中…
    </p>

    <div
      v-else-if="!items.length"
      class="card flex flex-col items-center gap-2 py-14 text-center"
    >
      <AppIcon name="trophy" :size="30" class="text-slate-600" />
      <p class="text-sm text-slate-400">这个时间段还没有人专注</p>
      <p class="text-xs text-slate-600">去做第一个，名字就会出现在这里。</p>
    </div>

    <template v-else>
      <div class="grid gap-4 sm:grid-cols-3">
        <div
          v-for="item in podium"
          :key="item.user_id"
          class="glass card-hover relative flex flex-col items-center gap-1.5 overflow-hidden p-5 text-center"
          :class="[RANK_STYLE[item.rank], isSelf(item) ? 'ring-1 ring-calm/40' : '']"
        >
          <div
            class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-current to-transparent opacity-50"
          />
          <span class="flex items-center gap-1 text-[11px] font-medium">
            <AppIcon name="trophy" :size="13" />
            NO.{{ item.rank }}
          </span>
          <span
            class="mt-1 flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-black/30 text-lg font-semibold"
          >
            {{ (item.nickname || '?').slice(0, 1).toUpperCase() }}
          </span>
          <span class="mt-1 max-w-full truncate text-sm text-slate-100">
            {{ item.nickname }}<span v-if="isSelf(item)" class="ml-1 text-[11px] text-calm">（我）</span>
          </span>
          <span class="num text-lg font-semibold text-slate-50">
            {{ formatDuration(item.duration) }}
          </span>
          <span class="text-[11px] text-slate-500">{{ item.session_count }} 次专注</span>
        </div>
      </div>

      <div v-if="rest.length" class="card">
        <div class="mb-3 flex items-center gap-1.5 text-sm text-slate-400">
          <AppIcon name="chart" :size="15" />
          其他同学
        </div>
        <div class="overflow-x-auto">
          <table class="data-table">
            <thead>
              <tr>
                <th class="w-16">名次</th>
                <th>用户</th>
                <th>专注时长</th>
                <th class="text-right">次数</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in rest"
                :key="item.user_id"
                :class="isSelf(item) ? 'bg-calm/[0.06]' : ''"
              >
                <td class="num text-slate-500">{{ item.rank }}</td>
                <td class="text-slate-200">
                  {{ item.nickname }}
                  <span v-if="isSelf(item)" class="ml-1 text-[11px] text-calm">（我）</span>
                </td>
                <td class="num text-slate-100">{{ formatDuration(item.duration) }}</td>
                <td class="num text-right text-slate-500">{{ item.session_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
