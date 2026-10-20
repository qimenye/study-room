<script setup>
import { onMounted, reactive, ref } from 'vue'

import AgentChat from '../components/AgentChat.vue'
import AppIcon from '../components/AppIcon.vue'
import LlmSettings from '../components/LlmSettings.vue'
import { agentApi } from '../api/agent'

const report = ref('')
const reportSource = ref('')
const reportNote = ref('')
const suggestion = ref('')
const reportLoading = ref(false)
const reportError = ref('')

const plan = reactive({ goal: '', weeks: 4, hours_per_week: 10 })
const planContent = ref('')
const planSource = ref('')
const planNote = ref('')
const plans = ref([])
const planLoading = ref(false)
const planError = ref('')

const sourceLabel = (value) => (value === 'llm' ? '大模型生成' : '本地模板兜底')

async function generateReport() {
  reportLoading.value = true
  reportError.value = ''
  try {
    const data = await agentApi.report(true)
    report.value = data.content
    reportSource.value = data.source
    reportNote.value = data.note || ''
    suggestion.value = data.suggestion || ''
  } catch (err) {
    reportError.value = err.message || '生成失败'
  } finally {
    reportLoading.value = false
  }
}

async function generatePlan() {
  if (!plan.goal.trim()) return
  planLoading.value = true
  planError.value = ''
  try {
    const data = await agentApi.createPlan({
      goal: plan.goal,
      weeks: Number(plan.weeks),
      hours_per_week: Number(plan.hours_per_week),
    })
    planContent.value = data.content
    planSource.value = data.source
    planNote.value = data.note || ''
    await loadPlans()
  } catch (err) {
    planError.value = err.message || '生成失败'
  } finally {
    planLoading.value = false
  }
}

async function loadPlans() {
  try {
    plans.value = await agentApi.plans()
  } catch {
    plans.value = []
  }
}

onMounted(loadPlans)
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h2 class="page-title">AI 助手</h2>
      <p class="mt-1 text-xs text-slate-500">
        报告和计划都基于你的真实专注数据；可以用服务端的 Key，也可以在下面填自己的。
      </p>
    </div>

    <LlmSettings />

    <div class="grid gap-5 lg:grid-cols-3">
      <div class="card flex flex-col gap-4 lg:col-span-2">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="flex items-center gap-1.5 text-sm text-slate-400">
            <AppIcon name="chart" :size="15" />
            学习报告
          </span>
          <div class="flex items-center gap-2">
            <span v-if="reportSource" class="tag">{{ sourceLabel(reportSource) }}</span>
            <button class="btn-primary" :disabled="reportLoading" @click="generateReport">
              <AppIcon name="refresh" :size="15" :class="reportLoading ? 'animate-spin' : ''" />
              {{ reportLoading ? '生成中…' : '生成报告' }}
            </button>
          </div>
        </div>

        <p v-if="reportError" class="text-xs text-rose-300">{{ reportError }}</p>
        <p
          v-if="reportNote"
          class="rounded-xl border border-amber-400/25 bg-amber-400/[0.07] px-3 py-2 text-xs leading-relaxed text-amber-200/90"
        >
          这份是本地统计（没连上大模型）：{{ reportNote }}
        </p>

        <div
          v-if="report"
          data-scroll-lock
          class="max-h-96 overflow-y-auto rounded-xl border border-white/10 bg-black/20 p-4"
        >
          <pre class="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-slate-300">{{ report }}</pre>
        </div>
        <div
          v-else
          class="flex flex-col items-center gap-2 rounded-xl border border-dashed border-white/10 py-10 text-center"
        >
          <AppIcon name="sparkles" :size="26" class="text-slate-600" />
          <p class="text-sm text-slate-400">还没有报告</p>
          <p class="text-xs text-slate-600">点右上角"生成报告"，会按你的真实数据写一份周报。</p>
        </div>

        <p
          v-if="suggestion"
          class="rounded-xl border border-calm/25 bg-calm/[0.06] px-3 py-2 text-xs leading-relaxed text-calm"
        >
          {{ suggestion }}
        </p>
      </div>

      <AgentChat />
    </div>

    <div class="grid gap-5 lg:grid-cols-2">
      <div class="card flex flex-col gap-4">
        <span class="flex items-center gap-1.5 text-sm text-slate-400">
          <AppIcon name="target" :size="15" />
          学习计划拆解
        </span>
        <div>
          <label class="label">你的目标</label>
          <input v-model="plan.goal" class="input" placeholder="例如：3 个月考研数学强化" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">周期（周）</label>
            <input v-model.number="plan.weeks" type="number" min="1" max="52" class="input" />
          </div>
          <div>
            <label class="label">每周投入（小时）</label>
            <input
              v-model.number="plan.hours_per_week"
              type="number"
              min="1"
              max="100"
              class="input"
            />
          </div>
        </div>
        <button class="btn-primary" :disabled="planLoading || !plan.goal" @click="generatePlan">
          <AppIcon name="sparkles" :size="16" />
          {{ planLoading ? '生成中…' : '生成周计划' }}
        </button>
        <p v-if="planError" class="text-xs text-rose-300">{{ planError }}</p>
        <p v-if="planContent" class="text-[11px] text-slate-500">来源：{{ sourceLabel(planSource) }}</p>
        <p
          v-if="planNote"
          class="rounded-xl border border-amber-400/25 bg-amber-400/[0.07] px-3 py-2 text-xs leading-relaxed text-amber-200/90"
        >
          这份是本地模板（没连上大模型）：{{ planNote }}
        </p>
        <div
          v-if="planContent"
          data-scroll-lock
          class="max-h-80 overflow-y-auto rounded-xl border border-white/10 bg-black/20 p-4"
        >
          <pre class="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-slate-300">{{ planContent }}</pre>
        </div>
      </div>

      <div class="card flex flex-col gap-3">
        <span class="flex items-center gap-1.5 text-sm text-slate-400">
          <AppIcon name="calendar" :size="15" />
          历史计划
        </span>
        <p v-if="!plans.length" class="text-xs text-slate-500">还没有保存的计划。</p>
        <div
          v-for="item in plans"
          :key="item.id"
          class="rounded-xl border border-white/10 bg-white/[0.03] p-3"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="truncate text-sm text-slate-200">{{ item.goal }}</span>
            <span class="tag shrink-0">{{ item.weeks }} 周</span>
          </div>
          <div data-scroll-lock class="mt-2 max-h-40 overflow-y-auto">
            <pre class="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-slate-400">{{ item.content }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
