<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import AppIcon from './AppIcon.vue'
import { musicApi } from '../api/music'

const props = defineProps({
  state: { type: Object, default: null },
})
const emit = defineEmits(['changed', 'close'])

const QR_TEXT = {
  idle: '',
  loading: '正在生成二维码…',
  waiting: '等待扫码',
  scanned: '已扫码，请在手机上确认',
  confirmed: '登录成功',
  expired: '二维码已过期，点刷新重新生成',
  error: '二维码生成失败',
}

const method = ref('qr')
const notice = ref('')
const noticeOk = ref(false)

const qr = ref(null)
const qrState = ref('idle')
const qrMessage = ref('')
let qrTimer = null
let qrDeadline = 0

const phone = ref('')
const countryCode = ref('86')
const captcha = ref('')
const sending = ref(false)
const logging = ref(false)
const countdown = ref(0)
let countdownTimer = null

const cookieInput = ref('')
const savingCookie = ref(false)
const testingCookie = ref(false)

const hasCookie = computed(() => Boolean(props.state?.has_cookie))
const nickname = computed(() => props.state?.nickname || '')
const qrText = computed(() => QR_TEXT[qrState.value] || qrMessage.value)

function notify(text, ok) {
  notice.value = text
  noticeOk.value = ok
}

function stopQrPolling() {
  if (qrTimer !== null) {
    window.clearTimeout(qrTimer)
    qrTimer = null
  }
}

async function startQr(force = false) {
  if (!force && ['loading', 'waiting', 'scanned'].includes(qrState.value)) return
  stopQrPolling()
  qr.value = null
  qrState.value = 'loading'
  qrMessage.value = ''
  notify('', true)
  try {
    const data = await musicApi.loginQr()
    qr.value = data
    qrDeadline = Date.now() + Number(data.expires_in || 180) * 1000
    qrState.value = 'waiting'
    qrTimer = window.setTimeout(pollQr, 1200)
  } catch (err) {
    qrState.value = 'error'
    qrMessage.value = err.message || '生成二维码失败'
  }
}

async function pollQr() {
  if (!qr.value) return
  if (Date.now() > qrDeadline) {
    qrState.value = 'expired'
    return
  }
  try {
    const data = await musicApi.qrStatus(qr.value.key, qr.value.session)
    qrState.value = data.status || 'waiting'
    qrMessage.value = data.message || ''
    if (data.status === 'confirmed') {
      stopQrPolling()
      await finishLogin(data.nickname)
      return
    }
    if (data.status === 'expired') return
    qrTimer = window.setTimeout(pollQr, 2000)
  } catch (err) {
    if (err.status === 401) {
      qrState.value = 'error'
      qrMessage.value = '登录过期了，刷新页面重新登录'
      return
    }
    if (err.status === 400) {
      qrState.value = 'error'
      qrMessage.value = err.message || '二维码状态异常，请刷新重试'
      return
    }
    if (Date.now() < qrDeadline) {
      qrTimer = window.setTimeout(pollQr, 3000)
      return
    }
    qrState.value = 'error'
    qrMessage.value = err.message || '二维码状态查询失败'
  }
}

async function finishLogin(name) {
  stopQrPolling()
  notify('登录成功' + (name ? '：' + name : ''), true)
  let next = null
  try {
    next = await musicApi.settings()
  } catch {
    next = { ...(props.state || {}), has_cookie: true, source: 'user', nickname: name || '网易云用户' }
  }
  emit('changed', next)
  window.setTimeout(() => emit('close'), 700)
}

function startCountdown(seconds = 60) {
  countdown.value = seconds
  if (countdownTimer) window.clearInterval(countdownTimer)
  countdownTimer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      window.clearInterval(countdownTimer)
      countdownTimer = null
    }
  }, 1000)
}

async function sendCode() {
  const digits = phone.value.replace(/\D/g, '')
  if (!digits) {
    notify('先填手机号。', false)
    return
  }
  sending.value = true
  notice.value = ''
  try {
    const data = await musicApi.sendCaptcha({ phone: digits, country_code: countryCode.value })
    notify(data.message || '验证码已发送，注意查收短信', true)
    startCountdown(60)
  } catch (err) {
    notify(err.message || '验证码发送失败', false)
  } finally {
    sending.value = false
  }
}

async function submitPhone() {
  const digits = phone.value.replace(/\D/g, '')
  const code = captcha.value.replace(/\D/g, '')
  if (!digits) {
    notify('先填手机号。', false)
    return
  }
  if (code.length < 4) {
    notify('先填短信验证码。', false)
    return
  }
  logging.value = true
  notice.value = ''
  try {
    const data = await musicApi.phoneLogin({
      phone: digits,
      country_code: countryCode.value,
      captcha: code,
    })
    await finishLogin(data.nickname)
  } catch (err) {
    notify(err.message || '登录失败', false)
  } finally {
    logging.value = false
  }
}

async function saveCookie() {
  const text = cookieInput.value.trim()
  if (!text) {
    notify('先粘贴 Cookie。', false)
    return
  }
  savingCookie.value = true
  notice.value = ''
  try {
    const next = await musicApi.saveSettings({ cookie: text })
    emit('changed', next)
    cookieInput.value = ''
    notify('已保存，之后播放会用这个登录态。', true)
    stopQrPolling()
    window.setTimeout(() => emit('close'), 700)
  } catch (err) {
    notify(err.message || '保存失败', false)
  } finally {
    savingCookie.value = false
  }
}

async function testCookie() {
  testingCookie.value = true
  notice.value = ''
  try {
    const text = cookieInput.value.trim()
    const result = await musicApi.testSettings(text ? { cookie: text } : {})
    notify(result.message || (result.ok ? '可用' : '不可用'), Boolean(result.ok))
    if (result.ok) {
      const next = await musicApi.settings()
      emit('changed', next)
    }
  } catch (err) {
    notify(err.message || '测试失败', false)
  } finally {
    testingCookie.value = false
  }
}

async function logout() {
  if (!window.confirm('退出当前网易云账号？退出后 VIP 歌曲会放不了。')) return
  savingCookie.value = true
  notice.value = ''
  try {
    const next = await musicApi.clearSettings()
    emit('changed', next)
    notify('已退出网易云账号。', true)
    method.value = 'qr'
    qr.value = null
    qrState.value = 'idle'
    startQr(true)
  } catch (err) {
    notify(err.message || '退出失败', false)
  } finally {
    savingCookie.value = false
  }
}

onMounted(() => {
  if (!hasCookie.value) startQr()
})

onBeforeUnmount(() => {
  stopQrPolling()
  if (countdownTimer) window.clearInterval(countdownTimer)
})
</script>

<template>
  <div class="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3">
    <div class="flex items-center justify-between">
      <span class="flex items-center gap-1.5 text-xs text-slate-300">
        <AppIcon name="music" :size="14" class="text-calm" />
        网易云账号
      </span>
      <button class="text-slate-500 transition hover:text-slate-300" title="收起" @click="emit('close')">
        <AppIcon name="close" :size="15" />
      </button>
    </div>

    <template v-if="hasCookie">
      <div class="rounded-lg border border-calm/25 bg-calm/[0.06] px-3 py-2">
        <p class="text-xs text-calm">已登录{{ nickname ? '：' + nickname : '' }}</p>
        <p class="mt-0.5 text-[10px] text-slate-500">
          Cookie：{{ state?.cookie_masked || '已保存' }}
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <button class="btn-ghost px-3 py-1.5 text-xs" :disabled="testingCookie" @click="testCookie">
          {{ testingCookie ? '验证中…' : '验证登录' }}
        </button>
        <button class="btn-danger px-3 py-1.5 text-xs" :disabled="savingCookie" @click="logout">
          退出登录
        </button>
      </div>
      <p class="text-[10px] leading-relaxed text-slate-500">
        VIP / 高音质歌曲会用这个账号的权限。Cookie 只在本机后端，页面拿不到明文。
      </p>
    </template>

    <template v-else>
      <div class="flex rounded-lg border border-white/10 bg-black/20 p-0.5 text-[11px]">
        <button
          class="flex-1 rounded-md px-2 py-1 transition"
          :class="method === 'qr' ? 'bg-calm/15 text-calm' : 'text-slate-500 hover:text-slate-300'"
          @click="method = 'qr'"
        >
          扫码登录
        </button>
        <button
          class="flex-1 rounded-md px-2 py-1 transition"
          :class="method === 'phone' ? 'bg-calm/15 text-calm' : 'text-slate-500 hover:text-slate-300'"
          @click="method = 'phone'"
        >
          手机验证码
        </button>
        <button
          class="flex-1 rounded-md px-2 py-1 transition"
          :class="method === 'cookie' ? 'bg-calm/15 text-calm' : 'text-slate-500 hover:text-slate-300'"
          @click="method = 'cookie'"
        >
          手动 Cookie
        </button>
      </div>

      <div v-show="method === 'qr'" class="flex flex-col items-center gap-2">
        <div v-if="qrState === 'loading'" class="py-10 text-[11px] text-slate-500">正在生成二维码…</div>
        <template v-else-if="qr">
          <div class="rounded-xl bg-white p-2 shadow-lg">
            <img :src="qr.image" alt="网易云登录二维码" class="h-40 w-40" />
          </div>
          <p
            class="text-[11px]"
            :class="
              qrState === 'scanned'
                ? 'text-calm'
                : qrState === 'expired'
                  ? 'text-amber-300'
                  : 'text-slate-400'
            "
          >
            {{ qrText }}
          </p>
          <button class="btn-ghost px-3 py-1.5 text-xs" @click="startQr(true)">刷新二维码</button>
        </template>
        <button v-else class="btn-primary px-3 py-1.5 text-xs" @click="startQr(true)">
          {{ qrState === 'error' ? '重新生成二维码' : '生成登录二维码' }}
        </button>
        <p v-if="qrState === 'error'" class="text-[11px] text-rose-200">{{ qrMessage }}</p>
        <p class="text-center text-[10px] leading-relaxed text-slate-500">
          用网易云音乐 App 扫一扫，手机上点确认即可。二维码约 3 分钟有效。
        </p>
      </div>

      <div v-show="method === 'phone'" class="flex flex-col gap-2">
        <div class="flex gap-2">
          <label class="flex w-16 shrink-0 items-center gap-1 text-xs text-slate-500">
            +
            <input v-model="countryCode" class="input w-full px-2 text-center" maxlength="4" />
          </label>
          <input
            v-model="phone"
            class="input flex-1"
            inputmode="numeric"
            maxlength="15"
            placeholder="手机号"
          />
        </div>
        <div class="flex gap-2">
          <input
            v-model="captcha"
            class="input flex-1"
            inputmode="numeric"
            maxlength="8"
            placeholder="短信验证码"
          />
          <button
            class="btn-ghost shrink-0 px-3 text-xs"
            :disabled="sending || countdown > 0"
            @click="sendCode"
          >
            {{ countdown > 0 ? countdown + 's' : sending ? '发送中…' : '获取验证码' }}
          </button>
        </div>
        <button class="btn-primary px-3 py-1.5 text-xs" :disabled="logging" @click="submitPhone">
          {{ logging ? '登录中…' : '登录' }}
        </button>
        <p class="text-[10px] leading-relaxed text-slate-500">
          手机号和验证码由后端直接发给网易云，不会存到本项目的数据库。
        </p>
      </div>

      <div v-show="method === 'cookie'" class="flex flex-col gap-2">
        <input
          v-model="cookieInput"
          type="password"
          class="input"
          autocomplete="off"
          placeholder="粘贴 MUSIC_U 或整段 Cookie"
        />
        <div class="flex flex-wrap gap-2">
          <button class="btn-primary px-3 py-1.5 text-xs" :disabled="savingCookie" @click="saveCookie">
            {{ savingCookie ? '保存中…' : '保存' }}
          </button>
          <button class="btn-ghost px-3 py-1.5 text-xs" :disabled="testingCookie" @click="testCookie">
            {{ testingCookie ? '测试中…' : '测试' }}
          </button>
        </div>
        <p class="text-[10px] leading-relaxed text-slate-500">
          备用方式：浏览器登录 music.163.com 后按 F12 → Application/Storage → Cookies，复制
          <span class="text-slate-300">MUSIC_U</span>。
        </p>
      </div>

      <p
        v-if="notice"
        class="rounded-lg border px-2 py-1 text-[11px] leading-relaxed"
        :class="noticeOk ? 'border-calm/30 bg-calm/[0.06] text-calm' : 'border-rose-500/30 bg-rose-500/10 text-rose-200'"
      >
        {{ notice }}
      </p>
    </template>
  </div>
</template>
