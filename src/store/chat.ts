import { defineStore } from 'pinia'
import type { Message } from '../types'

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [] as Message[],
    isLoading: false,
    // 修改1：默认启用深色模式
    isDarkTheme: true,
    isDeepThinking: false,
    sessions: [
      { id: '1', title: '新对话', messages: [] as Message[] },
    ],
    currentSessionId: '1',
  }),
  actions: {
    addMessage(message: Message) {
      this.messages.push(message)
      const session = this.sessions.find(s => s.id === this.currentSessionId)
      if (session) {
        session.messages.push(message)
        // 更新会话标题为第一条用户消息
        if (message.role === 'user' && session.title === '新对话') {
          session.title = message.content.slice(0, 20) + (message.content.length > 20 ? '...' : '')
        }
      }
    },
    setLoading(loading: boolean) {
      this.isLoading = loading
    },
    clearMessages() {
      this.messages = []
    },
    toggleTheme() {
      this.isDarkTheme = !this.isDarkTheme
    },
    toggleDeepThinking() {
      this.isDeepThinking = !this.isDeepThinking
    },
    createNewSession() {
      const newSession = {
        id: Date.now().toString(),
        title: '新对话',
        messages: [] as Message[],
      }
      this.sessions.push(newSession)
      this.currentSessionId = newSession.id
      this.messages = []
    },
    switchSession(sessionId: string) {
      const session = this.sessions.find(s => s.id === sessionId)
      if (session) {
        this.currentSessionId = sessionId
        this.messages = session.messages
      }
    },
  },
})