<script setup>
import { computed, onMounted, ref } from 'vue'

import AppIcon from './AppIcon.vue'
import { settingsApi } from '../api/settings'

const data = ref(null)
const form = ref({ provider: 'deepseek', base_url: '', model: '', api_key: '' })
const open = ref(false)
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const message = ref('')
const messageOk = ref(false)

const providers = computed(() => data.value?.providers || [])
const preset = computed(() => providers.value.find((item) => item.key === form.value.provider) || null)
const needsKey = computed(() => (preset.value ? preset.value.need_key : true))

const SOURCE = {
  user: { text: '用你自己填的 Key', cls: 'badge-live' },
  env: { text: '用服务端 .env', cls: 'tag' },
  none: { text: '未配置 · 模板兜底', cls: 'tag' },
}
const source = computed(() => SOURCE[data.value?.source] || SOURCE.none)

const keyPlaceholder = computed(() => {
  if (data.value?.has_key) return '已保存 ' + data.value.key_masked + '（留空表示不修改）'
  return needsKey.value ? '粘贴 API Key，例如 sk-xxxxxxxx' : '本地 Ollama 不需要 Key'
})

/** 名字里带这些词的基本是"推理模型"：先输出一大段思考，稍慢且更费额度 */
const REASONING_HINT = /(reasoner|reasoning|thinking|-r1\b|flash)/i
const looksReasoning = computed(() => REASONING_HINT.test(form.value.model || ''))

function fill(state) {
  data.value = state
  form.value = {
    provider: state.provider || 'deepseek',
    base_url: state.base_url || '',
    model: state.model || '',
    api_key: '',
  }
}

function notify(text, ok) {
  message.value = text
  messageOk.value = ok
}

async function load() {
  loading.value = true
  try {
    const state = await settingsApi.llm()
    fill(state)
    open.value = state.source === 'none'
  } catch (err) {
    notify(err.message || '读取设置失败', false)
  } finally {
    loading.value = false
  }
}

function pickProvider(key) {
  const item = providers.value.find((entry) => entry.key === key)
  form.value.provider = key
  if (item) {
    form.value.base_url = item.base_url
    form.value.model = item.models[0] || ''
  }
  message.value = ''
}

/** 不传 api_key 就是不修改已存的那把；传了就是覆盖 */
function payload() {
  const body = {
    provider: form.value.provider,
    base_url: form.value.base_url.trim(),
    model: form.value.model.trim(),
  }
  const typed = form.value.api_key.trim()
  if (typed) body.api_key = typed
  return body
}

async function save() {
  saving.value = true
  message.value = ''
  try {
    fill(await settingsApi.saveLlm(payload()))
    notify('已保存，之后 AI 就用这份配置；填错了随时可以改回来。', true)
  } catch (err) {
    notify(err.message || '保存失败', false)
  } finally {
    saving.value = false
  }
}

async function test() {
  testing.value = true
  message.value = ''
  try {
    const result = await settingsApi.testLlm(payload())
    notify(result.message, Boolean(result.ok))
  } catch (err) {
    notify(err.message || '测试失败', false)
  } finally {
    testing.value = false
  }
}

async function clearMine() {
  if (!window.confirm('清除你自己填的 Key？清除后会回落到服务端配置（没有就继续用模板兜底）。')) return
  saving.value = true
  try {
    fill(await settingsApi.clearLlm())
    notify('已清除你自己的配置。', true)
  } catch (err) {
    notify(err.message || '清除失败', false)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="card flex flex-col gap-4">
    <button class="flex w-full items-center gap-2 text-left" @click="open = !open">
      <span class="flex items-center gap-1.5 text-sm text-slate-400">
        <AppIcon name="settings" :size="15" />
        模型设置（自带 API Key）
      </span>
      <span class="ml-auto flex items-center gap-2">
        <span :class="source.cls" class="whitespace-nowrap text-[11px]">{{ source.text }}</span>
        <AppIcon :name="open ? 'chevronUp' : 'chevronDown'" :size="15" class="text-slate-500" />
      </span>
    </button>

    <p v-if="loading" class="text-xs text-slate-500">读取中…</p>

    <template v-else-if="open">
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="item in providers"
          :key="item.key"
          class="chip"
          :class="form.provider === item.key ? 'chip-active' : 'hover:border-calm/40 hover:text-calm'"
          :title="item.note"
          @click="pickProvider(item.key)"
        >
          {{ item.label }}
        </button>
      </div>

      <p v-if="preset" class="text-[11px] leading-relaxed text-slate-500">{{ preset.note }}</p>

      <div class="grid gap-3 sm:grid-cols-2">
        <div class="sm:col-span-2">
          <label class="label">接口地址（OpenAI 兼容的 base_url）</label>
          <input v-model="form.base_url" class="input" placeholder="https://api.deepseek.com/v1" />
        </div>
        <div>
          <label class="label">模型名</label>
          <input v-model="form.model" class="input" placeholder="deepseek-chat" />
          <div v-if="preset && preset.models.length" class="mt-2 flex flex-wrap gap-1.5">
            <button
              v-for="name in preset.models"
              :key="name"
              class="tag hover:border-calm/40 hover:text-calm"
              @click="form.model = name"
            >
              {{ name }}
            </button>
          </div>
          <p
            v-if="looksReasoning"
            class="mt-2 rounded-lg border border-amber-400/25 bg-amber-400/[0.07] px-2 py-1 text-[11px] leading-relaxed text-amber-200/90"
          >
            这个模型名看着像「推理模型」：它会先输出一大段思考，生成长计划时容易只思考不回答，
            最后落到本地模板。日常用推荐 <button class="underline" @click="form.model = 'deepseek-chat'">deepseek-chat</button>。
          </p>
        </div>
        <div>
          <label class="label">API Key</label>
          <input
            v-model="form.api_key"
            type="password"
            class="input"
            autocomplete="off"
            :placeholder="keyPlaceholder"
            :disabled="!needsKey"
          />
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button class="btn-primary" :disabled="saving" @click="save">
          <AppIcon name="check" :size="15" />
          {{ saving ? '保存中…' : '保存' }}
        </button>
        <button class="btn-ghost" :disabled="testing" @click="test">
          <AppIcon name="bolt" :size="15" />
          {{ testing ? '测试中…' : '测试连接' }}
        </button>
        <button v-if="data?.has_key" class="btn-danger" @click="clearMine">
          <AppIcon name="trash" :size="15" />
          清除我的配置
        </button>
      </div>

      <p
        v-if="message"
        class="rounded-xl border px-3 py-2 text-xs leading-relaxed"
        :class="messageOk ? 'border-calm/30 bg-calm/[0.06] text-calm' : 'border-rose-500/30 bg-rose-500/10 text-rose-200'"
      >
        {{ message }}
      </p>

      <p class="text-[11px] leading-relaxed text-slate-500">
        Key 只保存在这台机器后端的数据库里，接口只回掩码（{{ data?.key_masked || '未保存' }}），页面拿不到明文；
        调用时由后端直接发给你填的接口地址。
        <span v-if="data?.source === 'env'">
          现在用的是服务端 .env 里的 Key，你在这里保存之后会优先用你的。
        </span>
        <span v-else-if="data?.source === 'none'">没有配 Key 时，所有 AI 功能继续用本地模板兜底。</span>
      </p>
    </template>
  </div>
</template>
