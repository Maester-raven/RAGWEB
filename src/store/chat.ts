import { defineStore } from 'pinia'
import type { Message } from '../types/chat'
import { deleteChatRecords, getChatRecords, getSessionsList } from '../api/chat'

type Session = { id: string; title: string; messages: Message[]; loaded: boolean }

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [] as Message[],
    isLoading: false,
    isDarkTheme: false,
    isDeepThinking: false,
    isShowThinking: false,
    isStreaming: true,
    sessions: [] as Session[],
    currentSessionId: '',
    currentUserId: localStorage.getItem('chat_user_id') ?? '',
  }),
  actions: {
    setUserId(userId: string) {
      this.currentUserId = userId
      localStorage.setItem('chat_user_id', userId)
    },
    addMessage(message: Message) {
      this.messages.push(message)
      const session = this.sessions.find(s => s.id === this.currentSessionId)
      if (session) {
        // 只有当 session.messages 与 this.messages 不是同一个引用时才单独 push，
        // 避免 switchSession 后两个变量指向同一数组导致重复添加
        if (session.messages !== this.messages) {
          session.messages.push(message)
        }
        if (message.role === 'user' && session.title === '新对话') {
          session.title = message.content.slice(0, 20) + (message.content.length > 20 ? '...' : '')
        }
      }
    },
    setLoading(loading: boolean) {
      this.isLoading = loading
    },
    async clearMessages() {
      this.messages = []
      const session = this.sessions.find(s => s.id === this.currentSessionId)
      if (session) {
        session.messages = []
        session.loaded = true
      }
      await deleteChatRecords(this.currentSessionId, this.currentUserId).catch(err => {
        console.error('清空数据库会话记录失败:', err)
      })
    },
    toggleTheme() {
      this.isDarkTheme = !this.isDarkTheme
    },
    toggleDeepThinking() {
      this.isDeepThinking = !this.isDeepThinking
    },
    toggleShowThinking() {
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
    removeMessage(id: string) {
      this.messages = this.messages.filter((m) => m.id !== id)
      const session = this.sessions.find((s) => s.id === this.currentSessionId)
      if (session) {
        session.messages = session.messages.filter((m) => m.id !== id)
      }
    },
    createNewSession() {
      const newSession: Session = {
        id: Date.now().toString(),
        title: '新对话',
        messages: [],
        loaded: true,
      }
      this.sessions.unshift(newSession)
      this.currentSessionId = newSession.id
      this.messages = []
    },
    async switchSession(sessionId: string) {
      const session = this.sessions.find(s => s.id === sessionId)
      if (!session) return
      this.currentSessionId = sessionId
      if (!session.loaded) {
        await this.loadMessagesForSession(sessionId)
      } else {
        this.messages = session.messages
      }
    },
    async loadMessagesForSession(sessionId: string) {
      try {
        const res = await getChatRecords(sessionId, this.currentUserId)
        const records: { id: string | number; role: 'user' | 'assistant'; content: string; create_time: string }[] = res.data.data
        const messages: Message[] = records.map(r => ({
          id: String(r.id),
          role: r.role,
          content: r.content,
          timestamp: new Date(r.create_time).getTime(),
        }))
        const session = this.sessions.find(s => s.id === sessionId)
        if (session) {
          session.messages = messages
          session.loaded = true
        }
        this.messages = messages
      } catch (err) {
        console.error('加载会话消息失败:', err)
        this.messages = []
      }
    },
    async loadSessionsFromDB() {
      if (!this.currentUserId) return
      try {
        const res = await getSessionsList(this.currentUserId)
        const dbSessions: { session_id: string; first_message: string | null; last_time: string }[] = res.data.data
        if (dbSessions.length === 0) {
          this.sessions = [{ id: Date.now().toString(), title: '新对话', messages: [], loaded: true }]
          this.currentSessionId = this.sessions[0]!.id
          this.messages = []
          return
        }
        this.sessions = dbSessions.map(s => ({
          id: s.session_id,
          title: s.first_message
            ? s.first_message.slice(0, 20) + (s.first_message.length > 20 ? '...' : '')
            : '新对话',
          messages: [],
          loaded: false,
        }))
        this.currentSessionId = this.sessions[0]!.id
        await this.loadMessagesForSession(this.sessions[0]!.id)
      } catch (err) {
        console.error('加载会话列表失败:', err)
        if (this.sessions.length === 0) {
          this.createNewSession()
        }
      }
    },
    async deleteSession(sessionId: string) {
      await deleteChatRecords(sessionId, this.currentUserId).catch(err => {
        console.error('删除数据库会话记录失败:', err)
      })
      this.sessions = this.sessions.filter(s => s.id !== sessionId)
      if (this.sessions.length > 0) {
        await this.switchSession(this.sessions[0]!.id)
      } else {
        this.createNewSession()
      }
    },
  },
})
