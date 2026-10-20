<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AgentChat from '../components/AgentChat.vue'
import AppIcon from '../components/AppIcon.vue'
import MemberSeat from '../components/MemberSeat.vue'
import PomodoroTimer from '../components/PomodoroTimer.vue'
import WhiteNoise from '../components/WhiteNoise.vue'
import { roomsApi } from '../api/rooms'
import { useRoomStore } from '../stores/room'
import { useTimerStore } from '../stores/timer'

const room = useRoomStore()
const timer = useTimerStore()
const route = useRoute()
const router = useRouter()

const chatInput = ref('')
const error = ref('')

const roomId = computed(() => Number(route.params.id))
const detail = computed(() => room.currentRoom)
const emptySeats = computed(() => {
  const max = detail.value?.max_users || 0
  return Math.max(0, max - room.members.length)
})

const legend = [
  { label: '专注中', dot: 'bg-calm shadow-[0_0_8px_1px_rgba(94,234,212,0.6)]', text: 'text-calm' },
  { label: '休息', dot: 'bg-slate-400', text: 'text-slate-400' },
  { label: '离开', dot: 'bg-slate-600', text: 'text-slate-500' },
]

onMounted(async () => {
  try {
    await roomsApi.join(roomId.value)
    await room.openRoom(roomId.value)
    await timer.restore()
  } catch (err) {
    error.value = err.message || '进入房间失败'
  }
})

onUnmounted(() => {
  room.closeRoom()
})

function sendChat() {
  const content = chatInput.value.trim()
  if (!content) return
  room.sendChat(content)
  chatInput.value = ''
}

async function leave() {
  if (timer.isActive && !window.confirm('还有进行中的专注，确定离开吗？')) return
  try {
    await roomsApi.leave(roomId.value)
  } catch {
    // 忽略
  }
  room.closeRoom()
  router.push({ name: 'rooms' })
}

async function start() {
  try {
    await timer.startSession(roomId.value)
  } catch {
    // 错误已在 store 中展示
  }
}

async function end() {
  try {
    await timer.endSession()
  } catch (err) {
    timer.error = err.message || '结束失败'
  }
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <div class="card-tight flex flex-wrap items-center gap-3">
      <button class="btn-ghost px-3" @click="leave">
        <AppIcon name="chevronUp" :size="16" class="rotate-[-90deg]" />
        返回
      </button>
      <div class="flex min-w-0 flex-col">
        <span class="truncate text-base font-medium text-slate-100">
          {{ detail?.name || '房间' }}
        </span>
        <span class="mt-0.5 flex items-center gap-2 text-[11px] text-slate-500">
          <span v-if="detail" class="tag">{{ detail.topic }}</span>
          <span class="inline-flex items-center gap-1">
            <AppIcon name="users" :size="12" />
            <span class="num">{{ room.onlineCount }}{{ detail ? '/' + detail.max_users : '' }}</span>
          </span>
          <span class="inline-flex items-center gap-1 text-calm">
            <span class="h-1.5 w-1.5 animate-breathe rounded-full bg-calm" />
            专注 {{ room.focusingCount }}
          </span>
        </span>
      </div>
      <span
        class="ml-auto inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px]"
        :class="
          room.connected
            ? 'border-calm/35 bg-calm/10 text-calm'
            : 'border-white/10 bg-white/[0.05] text-slate-500'
        "
      >
        <span class="h-1.5 w-1.5 rounded-full" :class="room.connected ? 'bg-calm' : 'bg-slate-500'" />
        {{ room.connected ? '实时已连接' : '连接中…' }}
      </span>
    </div>

    <p v-if="error" class="card-tight text-sm text-rose-300">{{ error }}</p>
    <p v-if="room.error" class="card-tight text-sm text-rose-300">{{ room.error }}</p>

    <div class="grid gap-5 lg:grid-cols-3">
      <div class="flex flex-col gap-5 lg:col-span-2">
        <div class="card">
          <div class="mb-4 flex items-center justify-between gap-3">
            <span class="flex items-center gap-1.5 text-sm text-slate-400">
              <AppIcon name="users" :size="15" />
              座位
            </span>
            <div class="hidden items-center gap-3 sm:flex">
              <span
                v-for="item in legend"
                :key="item.label"
                class="inline-flex items-center gap-1.5 text-[11px]"
                :class="item.text"
              >
                <span class="h-1.5 w-1.5 rounded-full" :class="item.dot" />
                {{ item.label }}
              </span>
            </div>
            <span class="tag">空位 {{ emptySeats }}</span>
          </div>

          <div class="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6">
            <MemberSeat
              v-for="(member, index) in room.members"
              :key="member.user_id"
              :member="member"
              :seat-index="member.seat ?? index"
              :is-self="member.user_id === room.selfUserId"
            />
            <div
              v-for="n in emptySeats"
              :key="'empty-' + n"
              class="flex flex-col items-center justify-center gap-1.5 rounded-2xl border border-dashed border-white/10 p-2.5 text-[11px] text-slate-600"
            >
              <div
                class="flex h-11 w-11 items-center justify-center rounded-2xl border border-dashed border-white/10"
              >
                {{ room.members.length + n }}
              </div>
              空位
            </div>
          </div>
        </div>

        <div class="card flex flex-col gap-3">
          <div class="flex items-center justify-between">
            <span class="flex items-center gap-1.5 text-sm text-slate-400">
              <AppIcon name="send" :size="15" />
              房间交流
            </span>
            <span class="text-[11px] text-slate-500">互相监督，别刷屏</span>
          </div>

          <div class="h-44 space-y-2 overflow-y-auto pr-1">
            <p
              v-if="!room.chats.length"
              class="rounded-xl border border-dashed border-white/10 px-3 py-2 text-xs text-slate-500"
            >
              还没有人发言，说句话打个招呼吧。
            </p>
            <div
              v-for="(item, index) in room.chats"
              :key="index"
              class="flex items-start gap-2.5"
            >
              <span
                class="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-white/[0.06] text-[11px] text-slate-300"
              >
                {{ (item.nickname || '?').slice(0, 1).toUpperCase() }}
              </span>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <span class="truncate text-[11px] text-slate-500">{{ item.nickname }}</span>
                  <span
                    v-if="item.user_id === room.selfUserId"
                    class="text-[10px] text-calm"
                  >
                    我
                  </span>
                </div>
                <p
                  class="mt-0.5 break-words rounded-xl px-3 py-1.5 text-sm"
                  :class="
                    item.user_id === room.selfUserId
                      ? 'bg-calm/10 text-slate-100'
                      : 'bg-white/[0.04] text-slate-300'
                  "
                >
                  {{ item.content }}
                </p>
              </div>
            </div>
          </div>

          <div class="flex gap-2">
            <input
              v-model="chatInput"
              class="input"
              placeholder="说点什么，互相监督…"
              @keyup.enter="sendChat"
            />
            <button class="btn-primary px-3.5" title="发送" @click="sendChat">
              <AppIcon name="send" :size="16" />
            </button>
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-5">
        <PomodoroTimer
          @start="start"
          @pause="timer.pauseSession"
          @resume="timer.resumeSession"
          @end="end"
        />
        <WhiteNoise :suggested="room.welcome?.sound || ''" />
        <div v-if="room.agentMessages.length" class="card flex flex-col gap-2">
          <span class="flex items-center gap-1.5 text-sm text-slate-400">
            <AppIcon name="sparkles" :size="15" class="text-calm" />
            房间氛围助手
          </span>
          <p
            v-for="(item, index) in room.agentMessages"
            :key="index"
            class="rounded-xl border border-calm/20 bg-calm/[0.06] px-3 py-2 text-xs leading-relaxed text-calm"
          >
            {{ item.content }}
          </p>
        </div>
        <AgentChat />
      </div>
    </div>
  </div>
</template>
