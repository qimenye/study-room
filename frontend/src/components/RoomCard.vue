<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  room: { type: Object, required: true },
})
defineEmits(['enter', 'remove'])
</script>

<template>
  <div class="card card-hover relative flex flex-col gap-4 overflow-hidden">
    <div
      class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-calm/60 to-transparent"
    />

    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <h3 class="truncate text-base font-medium text-slate-100">{{ room.name }}</h3>
        <p class="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-500">
          {{ room.description || '暂无描述' }}
        </p>
      </div>
      <span v-if="room.is_official" class="badge-live shrink-0">
        <AppIcon name="bolt" :size="12" />
        官方
      </span>
    </div>

    <div class="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs">
      <span class="tag">{{ room.topic }}</span>
      <span class="inline-flex items-center gap-1 text-slate-400">
        <AppIcon name="users" :size="13" />
        <span class="num">{{ room.online_count }}/{{ room.max_users }}</span>
      </span>
      <span v-if="room.focusing_count" class="inline-flex items-center gap-1.5 text-calm">
        <span class="h-1.5 w-1.5 animate-breathe rounded-full bg-calm" />
        专注 {{ room.focusing_count }}
      </span>
      <span v-else class="text-slate-600">暂时没人专注</span>
    </div>

    <div class="mt-auto flex gap-2">
      <button class="btn-primary flex-1" @click="$emit('enter', room)">
        <AppIcon name="door" :size="15" />
        进入房间
      </button>
      <button
        v-if="!room.is_official"
        class="btn-icon"
        title="删除房间"
        @click="$emit('remove', room)"
      >
        <AppIcon name="trash" :size="16" />
      </button>
    </div>
  </div>
</template>