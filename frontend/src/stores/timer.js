import { defineStore } from 'pinia'

import { sessionsApi } from '../api/sessions'
import { agentApi } from '../api/agent'
import { useRoomStore } from './room'
import { useUserStore } from './user'

let worker = null

export const useTimerStore = defineStore('timer', {
  state: () => ({
    mode: 'pomodoro',
    plannedMinutes: 25,
    status: 'idle', // idle | running | paused
    elapsed: 0,
    sessionId: null,
    lastSummary: '',
    lastMessage: '',
    error: '',
    restoreAttempted: false,
  }),
  getters: {
    plannedSeconds: (state) => state.plannedMinutes * 60,
    isActive: (state) => state.status === 'running' || state.status === 'paused',
    remaining: (state) => Math.max(0, state.plannedMinutes * 60 - state.elapsed),
    displaySeconds: (state) =>
      state.mode === 'countup' ? state.elapsed : Math.max(0, state.plannedMinutes * 60 - state.elapsed),
    progress: (state) => {
      if (state.mode === 'countup') return 0
      const planned = state.plannedMinutes * 60
      if (!planned) return 0
      return Math.min(1, state.elapsed / planned)
    },
    statusText: (state) => ({ idle: '未开始', running: '专注中', paused: '已暂停' }[state.status] || state.status),
  },
  actions: {
    ensureWorker() {
      if (worker) return worker
      worker = new Worker(new URL('../workers/timerWorker.js', import.meta.url), { type: 'module' })
      worker.onmessage = (event) => {
        const data = event.data || {}
        if (data.type === 'tick' || data.type === 'synced' || data.type === 'paused') {
          this.handleElapsed(data.elapsed)
        }
      }
      return worker
    },

    handleElapsed(elapsed) {
      this.elapsed = Math.max(0, Math.floor(elapsed || 0))
      if (this.mode === 'pomodoro' && this.status === 'running' && this.elapsed >= this.plannedMinutes * 60) {
        this.finishByTimer()
      }
    },

    setMode(mode, minutes) {
      if (this.isActive) return
      this.mode = mode
      if (minutes) this.plannedMinutes = minutes
      this.elapsed = 0
    },

    notify(title, body) {
      try {
        if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
          new Notification(title, { body })
        }
      } catch {
        // 通知失败不影响主流程
      }
    },

    async startSession(roomId) {
      this.error = ''
      const room = useRoomStore()
      try {
        const session = await sessionsApi.start({
          room_id: roomId || room.currentRoomId || null,
          mode: this.mode,
          planned_minutes: this.plannedMinutes,
        })
        this.sessionId = session.id
        this.status = 'running'
        this.elapsed = 0
        const instance = this.ensureWorker()
        instance.postMessage({ type: 'reset' })
        instance.postMessage({ type: 'start' })
        room.setStatus('focusing')
        room.sendTimerState(this.snapshot())
        if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
          Notification.requestPermission().catch(() => {})
        }
        this.pushEncourage('start')
        return session
      } catch (error) {
        this.error = error.message || '开始失败'
        throw error
      }
    },

    async pauseSession() {
      if (!this.sessionId || this.status !== 'running') return
      const room = useRoomStore()
      await sessionsApi.pause(this.sessionId)
      this.status = 'paused'
      this.ensureWorker().postMessage({ type: 'pause' })
      room.setStatus('resting')
      room.sendTimerState(this.snapshot())
    },

    async resumeSession() {
      if (!this.sessionId || this.status !== 'paused') return
      const room = useRoomStore()
      await sessionsApi.resume(this.sessionId)
      this.status = 'running'
      this.ensureWorker().postMessage({ type: 'start' })
      room.setStatus('focusing')
      room.sendTimerState(this.snapshot())
    },

    async endSession() {
      if (!this.sessionId) return null
      const room = useRoomStore()
      const user = useUserStore()
      const session = await sessionsApi.end(this.sessionId)
      this.ensureWorker().postMessage({ type: 'pause' })
      this.ensureWorker().postMessage({ type: 'reset' })

      const minutes = Math.round((session.duration || 0) / 60)
      this.lastSummary = session.completed
        ? '完成 ' + minutes + ' 分钟，按计划达成。'
        : '本次专注 ' + minutes + ' 分钟。'

      this.sessionId = null
      this.status = 'idle'
      this.elapsed = 0
      room.setStatus('resting')
      room.sendTimerState(this.snapshot())
      user.fetchMe().catch(() => {})
      this.pushEncourage('finish', minutes)
      return session
    },

    async finishByTimer() {
      const minutes = this.plannedMinutes
      this.notify('专注结束', '完成 ' + minutes + ' 分钟，休息一下吧。')
      try {
        await this.endSession()
        this.lastMessage = '番茄钟完成，记录已保存。'
      } catch (error) {
        this.error = error.message || '结束失败'
      }
    },

    async pushEncourage(scene, minutes = 0) {
      const room = useRoomStore()
      try {
        const data = await agentApi.encourage({
          room_id: room.currentRoomId,
          scene,
          duration_minutes: minutes,
        })
        if (data && data.message) {
          room.pushAgentMessage(data.message)
          this.lastMessage = data.message
        }
      } catch {
        // 智能体不可用时静默降级
      }
    },

    snapshot() {
      return {
        mode: this.mode,
        status: this.status,
        elapsed: this.elapsed,
        planned_minutes: this.plannedMinutes,
        session_id: this.sessionId,
      }
    },

    async restore() {
      if (this.restoreAttempted) return
      this.restoreAttempted = true
      try {
        const data = await sessionsApi.active()
        const session = data.session
        if (!session) return
        this.mode = session.mode
        this.plannedMinutes = session.planned_minutes
        this.sessionId = session.id
        this.status = session.status === 'paused' ? 'paused' : 'running'
        this.elapsed = data.elapsed_seconds || 0
        const instance = this.ensureWorker()
        instance.postMessage({ type: 'sync', elapsed: this.elapsed })
        if (this.status === 'running') instance.postMessage({ type: 'start' })
        useRoomStore().setStatus(this.status === 'running' ? 'focusing' : 'resting')
      } catch {
        // 没有进行中的会话是正常情况
      }
    },

    reset() {
      if (worker) {
        worker.postMessage({ type: 'reset' })
      }
      this.sessionId = null
      this.status = 'idle'
      this.elapsed = 0
      this.restoreAttempted = false
    },
  },
})