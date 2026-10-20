<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  pages: { type: Array, required: true },
  index: { type: Number, default: -1 },
})

defineEmits(['select', 'step'])
</script>

<template>
  <div
    class="fixed right-2 top-1/2 z-30 hidden -translate-y-1/2 flex-col items-center gap-1.5 rounded-full border border-white/10 bg-black/40 p-1.5 backdrop-blur-xl lg:flex"
  >
    <button
      class="flex h-7 w-7 items-center justify-center rounded-full text-slate-400 transition hover:text-calm disabled:opacity-25 disabled:hover:text-slate-400"
      :disabled="index <= 0"
      title="上一页"
      @click="$emit('step', -1)"
    >
      <AppIcon name="chevronUp" :size="14" />
    </button>

    <button
      v-for="(page, i) in pages"
      :key="page.name"
      class="group relative flex h-4 w-4 items-center justify-center"
      :title="page.label"
      @click="$emit('select', i)"
    >
      <span
        class="h-2 w-2 rounded-full transition"
        :class="
          i === index
            ? 'bg-calm shadow-[0_0_10px_2px_rgba(94,234,212,0.45)]'
            : 'bg-white/25 group-hover:bg-white/50'
        "
      />
      <span
        class="pointer-events-none absolute right-6 hidden whitespace-nowrap rounded-lg border border-white/10 bg-black/75 px-2 py-1 text-[11px] text-slate-200 group-hover:block"
      >
        {{ page.label }}
      </span>
    </button>

    <button
      class="flex h-7 w-7 items-center justify-center rounded-full text-slate-400 transition hover:text-calm disabled:opacity-25 disabled:hover:text-slate-400"
      :disabled="index >= pages.length - 1"
      title="下一页"
      @click="$emit('step', 1)"
    >
      <AppIcon name="chevronDown" :size="14" />
    </button>
  </div>
</template>
