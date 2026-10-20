<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppIcon from '../components/AppIcon.vue'
import RoomCard from '../components/RoomCard.vue'
import { useRoomStore } from '../stores/room'

const room = useRoomStore()
const router = useRouter()

const topicFilter = ref('')
const showForm = ref(false)
const creating = ref(false)
const refreshing = ref(false)
const error = ref('')
const form = reactive({ name: '', topic: '自习', description: '', max_users: 12 })

const topics = ['自习', '考研', '编程', '阅读', '外语', '写作']

onMounted(() => {
  room.loadRooms().catch(() => {})
})

const list = computed(() => room.rooms || [])

const filtered = computed(() =>
  topicFilter.value ? list.value.filter((item) => item.topic === topicFilter.value) : list.value,
)

const summary = computed(() => [
  { label: '开放房间', value: list.value.length, icon: 'door' },
  {
    label: '在线同学',
    value: list.value.reduce((total, item) => total + (item.online_count || 0), 0),
    icon: 'users',
  },
  {
    label: '正在专注',
    value: list.value.reduce((total, item) => total + (item.focusing_count || 0), 0),
    icon: 'flame',
  },
])

async function refresh() {
  refreshing.value = true
  try {
    await room.loadRooms()
  } catch {
    // 保持旧列表即可
  } finally {
    refreshing.value = false
  }
}

async function create() {
  error.value = ''
  creating.value = true
  try {
    const created = await room.createRoom({
      name: form.name,
      topic: form.topic,
      description: form.description,
      max_users: Number(form.max_users),
    })
    showForm.value = false
    form.name = ''
    form.description = ''
    router.push({ name: 'room-detail', params: { id: created.id } })
  } catch (err) {
    error.value = err.message || '创建失败'
  } finally {
    creating.value = false
  }
}

async function remove(target) {
  if (!window.confirm('确定删除房间「' + target.name + '」吗？')) return
  try {
    await room.removeRoom(target.id)
  } catch (err) {
    window.alert(err.message || '删除失败')
  }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h2 class="page-title">自习室</h2>
        <p class="mt-1 text-xs text-slate-500">挑一个房间坐下，或者自己开一间。</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn-icon" title="刷新列表" @click="refresh">
          <AppIcon name="refresh" :size="17" :class="refreshing ? 'animate-spin' : ''" />
        </button>
        <button class="btn-primary" @click="showForm = !showForm">
          <AppIcon :name="showForm ? 'chevronUp' : 'plus'" :size="16" />
          {{ showForm ? '收起表单' : '创建房间' }}
        </button>
      </div>
    </div>

    <div class="grid gap-3 sm:grid-cols-3">
      <div v-for="item in summary" :key="item.label" class="card-tight flex items-center gap-3">
        <span class="flex h-9 w-9 items-center justify-center rounded-xl bg-white/[0.05] text-calm">
          <AppIcon :name="item.icon" :size="17" />
        </span>
        <span class="flex flex-col">
          <span class="text-[11px] text-slate-500">{{ item.label }}</span>
          <span class="num text-lg leading-tight text-slate-100">{{ item.value }}</span>
        </span>
      </div>
    </div>

    <Transition name="page">
      <form v-if="showForm" class="card grid gap-4 sm:grid-cols-2" @submit.prevent="create">
        <div class="sm:col-span-2 flex items-center gap-2 text-sm text-slate-300">
          <AppIcon name="plus" :size="15" class="text-calm" />
          新房间
        </div>
        <div>
          <label class="label">房间名</label>
          <input v-model="form.name" class="input" placeholder="例如：晚自习冲刺" />
        </div>
        <div>
          <label class="label">主题</label>
          <select v-model="form.topic" class="input">
            <option v-for="topic in topics" :key="topic" :value="topic">{{ topic }}</option>
          </select>
        </div>
        <div>
          <label class="label">描述</label>
          <input v-model="form.description" class="input" placeholder="这个房间的规则或目标" />
        </div>
        <div>
          <label class="label">人数上限（2-50）</label>
          <input v-model.number="form.max_users" type="number" min="2" max="50" class="input" />
        </div>
        <div class="sm:col-span-2 flex items-center gap-3">
          <button class="btn-primary" type="submit" :disabled="creating || !form.name">
            <AppIcon name="check" :size="16" />
            {{ creating ? '创建中…' : '创建并进入' }}
          </button>
          <p v-if="error" class="text-xs text-rose-300">{{ error }}</p>
        </div>
      </form>
    </Transition>

    <div class="flex flex-wrap items-center gap-2">
      <button
        class="chip"
        :class="topicFilter === '' ? 'chip-active' : 'hover:border-calm/40 hover:text-calm'"
        @click="topicFilter = ''"
      >
        全部
        <span class="num text-[10px] opacity-70">{{ list.length }}</span>
      </button>
      <button
        v-for="topic in topics"
        :key="topic"
        class="chip"
        :class="topicFilter === topic ? 'chip-active' : 'hover:border-calm/40 hover:text-calm'"
        @click="topicFilter = topic"
      >
        {{ topic }}
      </button>
    </div>

    <div v-if="room.loading && !list.length" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="n in 3" :key="n" class="glass h-40 animate-pulse" />
    </div>

    <div
      v-else-if="!filtered.length"
      class="card flex flex-col items-center gap-2 py-12 text-center"
    >
      <AppIcon name="door" :size="30" class="text-slate-600" />
      <p class="text-sm text-slate-400">这个主题下还没有房间</p>
      <p class="text-xs text-slate-600">换个主题看看，或者自己开一间。</p>
    </div>

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <RoomCard
        v-for="item in filtered"
        :key="item.id"
        :room="item"
        @enter="router.push({ name: 'room-detail', params: { id: item.id } })"
        @remove="remove"
      />
    </div>
  </div>
</template>
