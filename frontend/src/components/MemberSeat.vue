<script setup>
import { computed } from 'vue'

import { statusLabel } from '../utils/format'

const props = defineProps({
  member: { type: Object, required: true },
  isSelf: { type: Boolean, default: false },
  seatIndex: { type: Number, default: null },
})

const initial = computed(() => (props.member.nickname || props.member.username || '?').slice(0, 1).toUpperCase())
const focusing = computed(() => props.member.status === 'focusing')
const resting = computed(() => props.member.status === 'resting')

const ringClass = computed(() => {
  if (focusing.value) return 'ring-2 ring-calm/60 shadow-[0_0_28px_-6px_rgba(94,234,212,0.55)]'
  if (resting.value) return 'ring-1 ring-white/15'
  return 'ring-1 ring-white/10'
})
</script>

<template>
  <div
    class="group flex flex-col items-center gap-1.5 rounded-2xl border p-2.5 transition duration-300"
    :class="[
      isSelf ? 'border-calm/45 bg-calm/[0.07]' : 'border-white/10 bg-white/[0.025]',
      member.online ? 'hover:-translate-y-0.5 hover:border-white/20' : 'opacity-40',
    ]"
  >
    <div class="relative">
      <div
        class="flex h-11 w-11 items-center justify-center rounded-2xl text-base font-semibold transition"
        :class="[ringClass, focusing ? 'bg-calm/15 text-calm' : 'bg-white/[0.06] text-slate-300']"
      >
        {{ initial }}
      </div>
      <span
        v-if="focusing"
        class="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-calm shadow-[0_0_10px_2px_rgba(94,234,212,0.7)]"
      />
      <span
        v-if="seatIndex !== null"
        class="num absolute -left-1 -top-1 rounded-md border border-white/10 bg-black/50 px-1 text-[9px] leading-4 text-slate-500"
      >
        {{ seatIndex }}
      </span>
    </div>

    <span class="w-full truncate text-center text-[11px] text-slate-300">
      {{ member.nickname }}{{ isSelf ? '（我）' : '' }}
    </span>
    <span
      class="rounded-full px-1.5 py-0.5 text-[10px]"
      :class="
        focusing
          ? 'bg-calm/10 text-calm'
          : resting
            ? 'bg-white/[0.06] text-slate-400'
            : 'text-slate-500'
      "
    >
      {{ statusLabel(member.status) }}
    </span>
  </div>
</template>
