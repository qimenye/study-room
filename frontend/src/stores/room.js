import { defineStore } from 'pinia'

import { roomsApi } from '../api/rooms'
import { createRoomSocket } from '../socket/roomSocket'

// WebSocket 实例放在模块作用域，避免被 Vue 的响应式代理包装
let socket = null

export const useRoomStore = defineStore('room', {
  state: () => ({
    rooms: [],
    currentRoom: null,
    currentRoomId: null,
    members: [],
    stats: {},
    chats: [],
    agentMessages: [],
    welcome: null,
    connected: false,
    loading: false,
    selfUserId: null,
    error: '',
  }),
  getters: {
    onlineCount: (state) => state.stats.online_count || 0,
    focusingCount: (state) => state.stats.focusing_count || 0,
    selfMember(state) {
      return state.members.find((item) => item.user_id === state.selfUserId) || null
    },
  },
  actions: {
    async loadRooms() {
      this.loading = true
      try {
        this.rooms = await roomsApi.list()
      } finally {
        this.loading = false
      }
    },

    async createRoom(payload) {
      const room = await roomsApi.create(payload)
      this.rooms.unshift(room)
      return room
    },

    async removeRoom(roomId) {
      await roomsApi.remove(roomId)
      this.rooms = this.rooms.filter((item) => item.id !== roomId)
    },

    async openRoom(roomId) {
      this.error = ''
      this.chats = []
      this.agentMessages = []
      this.currentRoomId = roomId
      const detail = await roomsApi.detail(roomId)
      this.currentRoom = detail
      this.members = detail.members || []
      this.stats = {
        online_count: detail.online_count,
        focusing_count: detail.focusing_count,
      }
      this.connect(roomId)
      return detail
    },

    connect(roomId) {
      if (!socket) {
        socket = createRoomSocket()
        socket.on('open', () => {
          this.connected = true
        })
        socket.on('close', () => {
          this.connected = false
        })
        socket.on('room_state', (data) => {
          this.members = data.members || []
          this.stats = data.stats || {}
          if (data.self) this.selfUserId = data.self.user_id
          if (data.welcome) {
            this.welcome = data.welcome
            if (data.welcome.message) this.pushAgentMessage(data.welcome.message)
          }
        })
        socket.on('member_joined', (data) => {
          const member = data.member
          if (!member) return
          const index = this.members.findIndex((item) => item.user_id === member.user_id)
          if (index >= 0) this.members.splice(index, 1, member)
          else this.members.push(member)
          this.stats = data.stats || this.stats
        })
        socket.on('member_left', (data) => {
          this.members = (data.members || this.members.filter((item) => item.user_id !== data.user_id))
          this.stats = data.stats || this.stats
        })
        socket.on('status_change', (data) => {
          const member = this.members.find((item) => item.user_id === data.user_id)
          if (member) member.status = data.status
          this.stats = data.stats || this.stats
        })
        socket.on('chat', (data) => {
          this.chats.push(data)
          if (this.chats.length > 200) this.chats.shift()
        })
        socket.on('error', (data) => {
          if (data && data.message) this.error = data.message
        })
      }
      socket.connect(roomId)
    },

    closeRoom() {
      if (socket) socket.close()
      this.connected = false
      this.currentRoomId = null
      this.currentRoom = null
      this.members = []
      this.stats = {}
    },

    setStatus(status) {
      if (socket) socket.send({ type: 'status', status })
    },

    sendTimerState(payload) {
      if (socket) socket.send({ type: 'timer', payload })
    },

    sendChat(content) {
      if (socket) socket.send({ type: 'chat', content })
    },

    pushAgentMessage(content) {
      this.agentMessages.push({ content, created_at: new Date().toISOString() })
      if (this.agentMessages.length > 30) this.agentMessages.shift()
    },
  },
})