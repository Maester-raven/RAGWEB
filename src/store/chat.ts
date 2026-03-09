import { defineStore } from 'pinia'
import type { Message } from '../types/chat' // 修正类型导入路径
// 导入数据库删除接口
import { deleteChatRecords } from '../api/chat'

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
    // 改造：清空消息（同步数据库）
    async clearMessages() {
      this.messages = []
      // 清空当前会话的本地消息
      const session = this.sessions.find(s => s.id === this.currentSessionId)
      if (session) {
        session.messages = []
      }
      // 同步删除数据库中的会话记录（失败仅打印错误）
      await deleteChatRecords(this.currentSessionId).catch(err => {
        console.error('清空数据库会话记录失败:', err)
      })
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
    // 新增：删除会话（同步数据库）
    async deleteSession(sessionId: string) {
      // 1. 删除数据库中的会话记录
      await deleteChatRecords(sessionId).catch(err => {
        console.error('删除数据库会话记录失败:', err)
      })
      // 2. 删除本地会话
      this.sessions = this.sessions.filter(s => s.id !== sessionId)
      // 3. 切换到第一个会话（避免无会话，使用非空断言!修复TS错误）
      if (this.sessions.length > 0) {
        this.currentSessionId = this.sessions[0]!.id
        this.messages = this.sessions[0]!.messages
      } else {
        // 无会话时创建默认会话
        this.createNewSession()
      }
    },
  },
})