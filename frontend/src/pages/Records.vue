<script setup>
import { computed, onMounted, ref } from 'vue'

import AppIcon from '../components/AppIcon.vue'
import Heatmap from '../components/Heatmap.vue'
import { sessionsApi } from '../api/sessions'
import { formatDateTime, formatDuration } from '../utils/format'

const stats = ref(null)
const heatmap = ref({ days: [], max_duration: 0 })
const records = ref([])
const period = ref('week')
const loading = ref(false)

const periods = [
  { key: 'today', label: '今日' },
  { key: 'week', label: '本周' },
  { key: 'month', label: '本月' },
  { key: 'all', label: '全部' },
]

const cards = computed(() => [
  {
    label: '今日',
    value: stats.value?.today_duration || 0,
    extra: (stats.value?.today_count || 0) + ' 次专注',
    icon: 'clock',
  },
  { label: '本周', value: stats.value?.week_duration || 0, extra: '近 7 天累计', icon: 'calendar' },
  { label: '本月', value: stats.value?.month_duration || 0, extra: '自然月累计', icon: 'chart' },
  {
    label: '累计',
    value: stats.value?.total_duration || 0,
    extra: '连续 ' + (stats.value?.streak_days || 0) + ' 天',
    icon: 'flame',
  },
])

async function load() {
  loading.value = true
  try {
    const [statsData, heatmapData, recordsData] = await Promise.all([
      sessionsApi.stats(),
      sessionsApi.heatmap(180),
      sessionsApi.records(period.value, 100),
    ])
    stats.value = statsData
    heatmap.value = heatmapData
    records.value = recordsData
  } finally {
    loading.value = false
  }
}

async function changePeriod(value) {
  period.value = value
  loading.value = true
  try {
    records.value = await sessionsApi.records(value, 100)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h2 class="page-title">学习记录</h2>
      <p class="mt-1 text-xs text-slate-500">每一次坐下都算数，数据来自服务端记录。</p>
    </div>

    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div v-for="card in cards" :key="card.label" class="card card-hover relative overflow-hidden">
        <div
          class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-calm/50 to-transparent"
        />
        <div class="flex items-center justify-between">
          <span class="text-xs text-slate-500">{{ card.label }}</span>
          <AppIcon :name="card.icon" :size="15" class="text-slate-600" />
        </div>
        <div class="stat-value">{{ formatDuration(card.value) }}</div>
        <div class="mt-1 text-[11px] text-slate-500">{{ card.extra }}</div>
      </div>
    </div>

    <div class="card">
      <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
        <span class="flex items-center gap-1.5 text-sm text-slate-400">
          <AppIcon name="calendar" :size="15" />
          近 180 天热力图
        </span>
        <span class="text-xs text-slate-500">
          最长单次 {{ formatDuration(stats?.longest_duration || 0) }}
        </span>
      </div>
      <Heatmap :days="heatmap.days" :max-duration="heatmap.max_duration" />
    </div>

    <div class="card">
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <span class="flex items-center gap-1.5 text-sm text-slate-400">
          <AppIcon name="clock" :size="15" />
          专注明细
        </span>
        <div class="flex gap-1 rounded-xl border border-white/10 bg-black/20 p-1">
          <button
            v-for="item in periods"
            :key="item.key"
            class="rounded-lg px-3 py-1 text-xs transition"
            :class="
              period === item.key
                ? 'bg-calm/15 text-calm'
                : 'text-slate-400 hover:text-slate-200'
            "
            @click="changePeriod(item.key)"
          >
            {{ item.label }}
          </button>
        </div>
      </div>

      <p v-if="loading && !records.length" class="py-6 text-center text-sm text-slate-500">
        加载中…
      </p>
      <p v-else-if="!records.length" class="py-6 text-center text-sm text-slate-500">
        这个时间段还没有记录，去房间里坐一会儿吧。
      </p>
      <div v-else class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th class="w-52">开始时间</th>
              <th>模式</th>
              <th>时长</th>
              <th class="text-right">状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in records" :key="item.id">
              <td class="num text-slate-400">{{ formatDateTime(item.start_time) }}</td>
              <td>
                <span class="tag">
                  {{ item.mode === 'pomodoro' ? '番茄钟' : '正计时' }}
                </span>
              </td>
              <td class="num text-slate-100">{{ formatDuration(item.duration) }}</td>
              <td class="text-right">
                <span
                  class="inline-flex items-center gap-1 text-xs"
                  :class="item.completed ? 'text-calm' : 'text-slate-500'"
                >
                  <AppIcon :name="item.completed ? 'check' : 'info'" :size="13" />
                  {{ item.completed ? '已完成' : '未完成' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
