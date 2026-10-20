<script setup>
import { nextTick, ref } from 'vue'

import AppIcon from './AppIcon.vue'
import { agentApi } from '../api/agent'

const messages = ref([])
const input = ref('')
const loading = ref(false)
const error = ref('')
const scroller = ref(null)

const quick = ['我学不进去怎么办', '帮我安排今天的任务', '怎么保持专注']

async function scrollToBottom() {
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

async function send(text) {
  const content = (text || input.value).trim()
  if (!content || loading.value) return
  messages.value.push({ role: 'user', content })
  input.value = ''
  loading.value = true
  error.value = ''
  await scrollToBottom()
  try {
    const data = await agentApi.chat({ message: content })
    messages.value.push({
      role: 'assistant',
      content: data.reply,
      source: data.source,
      note: data.note || '',
    })
  } catch (err) {
    error.value = err.message || '发送失败'
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}
</script>

<template>
  <div class="card flex h-[27rem] flex-col gap-3">
    <div class="flex items-center justify-between">
      <span class="flex items-center gap-1.5 text-sm text-slate-400">
        <AppIcon name="sparkles" :size="15" />
        AI 学习助手
      </span>
      <span class="text-[11px] text-slate-500">已开启限流保护</span>
    </div>

    <div
      ref="scroller"
      data-scroll-lock
      class="flex-1 space-y-2.5 overflow-y-auto pr-1"
    >
      <div v-if="!messages.length" class="rounded-xl border border-dashed border-white/10 p-3">
        <p class="text-xs leading-relaxed text-slate-500">
          可以问我：今天该怎么安排、学不进去怎么办、某个计划怎么拆更合理。
          回答来自真实大模型；万一没连上，我会直接告诉你原因，而不是回一句套话。
        </p>
      </div>

      <div
        v-for="(message, index) in messages"
        :key="index"
        class="flex"
        :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          class="flex max-w-[85%] flex-col gap-1"
          :class="message.role === 'user' ? 'items-end' : 'items-start'"
        >
          <div
            class="rounded-2xl px-3.5 py-2 text-sm leading-relaxed"
            :class="
              message.role === 'user'
                ? 'rounded-br-md bg-calm/15 text-slate-100'
                : 'rounded-bl-md border border-white/10 bg-white/[0.05] text-slate-200'
            "
          >
            {{ message.content }}
          </div>
          <p
            v-if="message.role !== 'user' && message.note"
            class="rounded-lg border border-amber-400/25 bg-amber-400/[0.07] px-2 py-1 text-[11px] leading-relaxed text-amber-200/90"
          >
            没连上大模型：{{ message.note }}
          </p>
          <span
            v-else-if="message.role !== 'user' && message.source"
            class="text-[10px] text-slate-500"
          >
            {{ message.source === 'llm' ? '大模型生成' : '本地兜底' }}
          </span>
        </div>
      </div>

      <div v-if="loading" class="flex justify-start">
        <div class="flex items-center gap-1.5 rounded-2xl rounded-bl-md border border-white/10 bg-white/[0.05] px-3.5 py-2.5">
          <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
          <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style="animation-delay: 0.15s" />
          <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style="animation-delay: 0.3s" />
        </div>
      </div>
    </div>

    <div class="flex flex-wrap gap-1.5">
      <button
        v-for="item in quick"
        :key="item"
        class="chip hover:border-calm/45 hover:text-calm"
        @click="send(item)"
      >
        {{ item }}
      </button>
    </div>

    <div class="flex gap-2">
      <input v-model="input" class="input" placeholder="说点什么…" @keyup.enter="send()" />
      <button class="btn-primary px-3.5" :disabled="loading" title="发送" @click="send()">
        <AppIcon name="send" :size="16" />
      </button>
    </div>
    <p v-if="error" class="text-xs text-rose-300">{{ error }}</p>
  </div>
</template>
