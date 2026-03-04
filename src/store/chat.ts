import { defineStore } from 'pinia'
import type { Message } from '../types'

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [] as Message[],
    isLoading: false,
    // 默认启用浅色模式
    isDarkTheme: false,
    isDeepThinking: false,
    isShowThinking: true,// 思考过程显示控制
    isStreaming: false,  // 流式输出开关
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
    toggeleShowThinking() {
      this.isShowThinking = !this.isShowThinking
    },
    toggleStreaming() {
      this.isStreaming = !this.isStreaming
    },
    updateMessageContent(id: string, content: string) {
      const msg = this.messages.find((m) => m.id === id)
      if (msg) msg.content = content
      const session = this.sessions.find((s) => s.id === this.currentSessionId)
      const sessionMsg = session?.messages.find((m) => m.id === id)
      if (sessionMsg) sessionMsg.content = content
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