<template>
  <div class="chat-container" :class="{ 'dark-theme': chatStore.isDarkTheme }">
    <!-- 左侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-icon">AI</div>
        <span class="brand-name">AI 助手</span>
      </div>

      <button class="new-session-btn" @click="chatStore.createNewSession()">
        <span class="btn-icon">＋</span>
        <span>新对话</span>
      </button>

      <div class="session-section-title">最近对话</div>
      <div class="session-list">
        <div v-for="session in chatStore.sessions" :key="session.id"
          :class="['session-item', { active: session.id === chatStore.currentSessionId }]"
          @click="chatStore.switchSession(session.id)">
          <span class="session-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="13" height="13">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="currentColor"
                stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
          <span class="session-title">{{ session.title }}</span>
        </div>
      </div>

      <div class="sidebar-footer">
        <button class="theme-toggle-btn" @click="chatStore.toggleTheme()">
          <span class="theme-icon">
            <svg v-if="chatStore.isDarkTheme" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"
              width="14" height="14">
              <circle cx="12" cy="12" r="5" stroke="currentColor" stroke-width="2" />
              <path
                d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
                stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="14" height="14">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
          <span>{{ chatStore.isDarkTheme ? '浅色模式' : '深色模式' }}</span>
        </button>
      </div>
    </aside>

    <!-- 主聊天区 -->
    <main class="chat-main">
      <!-- 顶部标题栏 -->
      <div class="chat-header">
        <div class="header-title">
          <div class="header-avatar">AI</div>
          <div>
            <div class="header-name">AI 助手</div>
            <div class="header-status">
              <span class="status-dot"></span>
              在线
            </div>
          </div>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="message-list" ref="messageListRef">
        <div v-for="message in chatStore.messages" :key="message.id" :class="['message-row', message.role]">
          <div v-if="message.role === 'assistant'" class="avatar assistant-avatar">AI</div>
          <div class="bubble-wrapper">
            <div class="thinking-context"
              v-if="message.role === 'assistant' && chatStore.isDeepThinking && chatStore.isShowThinking && message.content.includes('<think>')">
              {{ getThinkContent(message.content) }}
            </div>
            <div class="message-bubble" :class="{ 'markdown-body': message.role === 'assistant' }"
              v-if="message.role === 'assistant'" v-html="renderMarkdown(getDisplayContent(message.content))"></div>
            <div class="message-bubble" v-else>{{ getDisplayContent(message.content) }}</div>
          </div>
          <div v-if="message.role === 'user'" class="avatar user-avatar">你</div>
        </div>

        <!-- 加载动画（流式模式下由气泡本身展示进度，不再显示三点动画）-->
        <div v-if="chatStore.isLoading && !chatStore.isStreaming" class="message-row assistant">
          <div class="avatar assistant-avatar">AI</div>
          <div class="bubble-wrapper">
            <div class="message-bubble loading-bubble">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部输入区 -->
      <div class="input-wrapper">
        <div class="input-box">
          <button class="deep-think-btn" :class="{ active: chatStore.isDeepThinking }"
            @click="chatStore.toggleDeepThinking()" title="深度思考">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="14" height="14">
              <path
                d="M9 18h6M10 22h4M12 2a7 7 0 0 1 7 7c0 2.5-1.3 4.7-3.3 6L15 17H9l-.7-2C6.3 13.7 5 11.5 5 9a7 7 0 0 1 7-7z"
                stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="btn-label">深度思考</span>
          </button>
          <textarea v-model="inputText" placeholder="发送消息给 AI 助手..." @keydown.enter.exact.prevent="handleSend"
            rows="1"></textarea>
          <button class="send-btn" @click="handleSend" :disabled="!inputText.trim() || chatStore.isLoading"
            title="发送 (Enter)">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M22 2L11 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                stroke-linejoin="round" />
              <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                stroke-linejoin="round" />
            </svg>
          </button>
        </div>
        <div class="input-hint">按 Enter 发送，Shift+Enter 换行</div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useChatStore } from '../store/chat'
import { sendMessage, sendMessageStream } from '../api/chat'
import type { Message, ChatRequest, HistoryItem } from '../types'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

const renderMarkdown = (content: string): string => {
  if (!content) return ''
  const raw = marked.parse(content) as string
  return DOMPurify.sanitize(raw)
}

const chatStore = useChatStore()
const inputText = ref('')
const messageListRef = ref<HTMLElement | null>(null)

const getThinkContent = (content: string) => {
  const start = content.indexOf('<think>')
  if (start === -1) return ''
  const end = content.indexOf('</think>', start)
  if (end === -1) {
    // </think> 尚未到达，流式进行中，显示 <think> 之后的所有内容
    return content.slice(start + 7).trim()
  }
  return content.slice(start + 7, end).trim()
}

const getDisplayContent = (content: string) => {
  const start = content.indexOf('<think>')
  if (start === -1) return content.trim()
  const end = content.indexOf('</think>', start)
  if (end === -1) {
    // 仍在思考中，普通气泡只显示 <think> 之前的内容（通常为空）
    return content.slice(0, start).trim()
  }
  // <think> 之前 + </think> 之后的内容合并显示
  return (content.slice(0, start) + content.slice(end + 8)).trim()
}

const scrollToBottom = async () => {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

const handleSend = async () => {
  // 1. 先检查输入和加载状态，若不满足直接返回
  if (!inputText.value.trim() || chatStore.isLoading) return

  // 2. 立即设置加载状态，锁定后续调用（核心修复）
  chatStore.setLoading(true)

  // 3. 构建并添加用户消息
  const userMessage: Message = {
    id: Date.now().toString(),
    content: inputText.value,
    role: 'user',
    timestamp: Date.now(),
  }
  chatStore.addMessage(userMessage)

  // 4. 清空输入框并滚动到底部
  inputText.value = ''
  scrollToBottom()

  // 5. 构建历史记录和请求参数
  const allMessages = chatStore.messages
  const history: HistoryItem[] = allMessages
    .slice(0, -1)
    .filter((m) => m.id !== 'welcome')
    .map((m) => ({ role: m.role, content: m.content }))

  const requestData: ChatRequest = {
    question: userMessage.content,
    history: history.length > 0 ? history : undefined,
    enable_thinking: chatStore.isDeepThinking,
    return_thinking: chatStore.isShowThinking,
  }

  // 6. 区分流式/普通模式处理
  if (chatStore.isStreaming) {
    // 流式模式：先添加空的 AI 消息，再逐步更新内容
    const assistantMessage: Message = {
      id: `stream-${Date.now()}`,
      content: '',
      role: 'assistant',
      timestamp: Date.now(),
    }
    chatStore.addMessage(assistantMessage)
    const msgId = assistantMessage.id
    let streamedContent = ''

    sendMessageStream(
      requestData,
      (chunk: string) => {
        streamedContent += chunk
        chatStore.updateMessageContent(msgId, streamedContent)
        scrollToBottom()
      },
      () => {
        chatStore.setLoading(false) // 流式结束后重置加载状态
        scrollToBottom()
      },
      (error: Error) => {
        console.error('流式传输错误:', error)
        if (!streamedContent) {
          chatStore.updateMessageContent(msgId, '抱歉，发送失败了，请稍后再试。')
        }
        chatStore.setLoading(false) // 错误时重置加载状态
        scrollToBottom()
      }
    )
  } else {
    // 普通模式：等待接口响应后添加 AI 消息
    try {
      const response = await sendMessage(requestData)
      const assistantMessage: Message = {
        id: Date.now().toString(),
        content: response.choices[0]?.message?.content ?? '（无响应内容）',
        role: 'assistant',
        timestamp: Date.now(),
      }
      chatStore.addMessage(assistantMessage)
      scrollToBottom()
    } catch (error) {
      console.error('发送消息失败:', error)
      chatStore.addMessage({
        id: Date.now().toString(),
        content: '抱歉，发送失败了，请稍后再试。',
        role: 'assistant',
        timestamp: Date.now(),
      })
      scrollToBottom()
    } finally {
      chatStore.setLoading(false) // 无论成功失败，都重置加载状态
    }
  }
}

onMounted(() => {
  if (chatStore.messages.length === 0) {
    chatStore.addMessage({
      id: 'welcome',
      content: '您好！我是 AI 助手，有什么我能帮您的吗？',
      role: 'assistant',
      timestamp: Date.now(),
    })
  }
  scrollToBottom()
})

watch(
  () => chatStore.isDarkTheme,
  (newVal) => {
    if (newVal) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  },
  { immediate: true }
)
</script>

<style scoped>
/* ===== CSS 变量 - 浅色模式（定义在组件根元素上，避免 scoped 失效问题）===== */
.chat-container {
  --bg: #F9E4A0;
  --sidebar-bg: #FFFDF0;
  --chat-bg: #FFFCEF;
  --surface: #FFFFFF;
  --border: #E9BE91;
  --text-primary: #554F4C;
  --text-secondary: #8B7055;
  --text-muted: #CF9267;
  --accent: #F3AF27;
  --accent-hover: #CF9267;
  --accent-light: #FEF3CC;
  --user-bubble: #F3AF27;
  --user-bubble-text: #554F4C;
  --ai-bubble: #FFFFFF;
  --ai-bubble-text: #554F4C;
  --shadow-sm: 0 1px 3px rgba(85, 79, 76, 0.08), 0 1px 2px rgba(85, 79, 76, 0.05);
  --shadow-md: 0 4px 12px rgba(85, 79, 76, 0.12);
  --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

  /* ===== 布局 ===== */
  display: flex;
  height: 100vh;
  background-color: var(--bg);
  color: var(--text-primary);
  font-family: var(--font);
  font-size: 15px;
  line-height: 1.6;
  overflow: hidden;
}

/* ===== 深色模式 ===== */
.chat-container.dark-theme {
  --bg: #2A2623;
  --sidebar-bg: #322D29;
  --chat-bg: #2F2A26;
  --surface: #3A3430;
  --border: #554F4C;
  --text-primary: #F9E4A0;
  --text-secondary: #E9BE91;
  --text-muted: #CF9267;
  --accent: #FFD253;
  --accent-hover: #F3AF27;
  --accent-light: rgba(243, 175, 39, 0.15);
  --user-bubble: #F3AF27;
  --user-bubble-text: #554F4C;
  --ai-bubble: #3A3430;
  --ai-bubble-text: #F9E4A0;
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
}

/* ===== 左侧边栏 ===== */
.sidebar {
  width: 260px;
  min-width: 260px;
  background-color: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 20px 12px;
  gap: 8px;
  transition: background-color 0.3s, border-color 0.3s;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px 16px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 4px;
}

.brand-icon {
  width: 34px;
  height: 34px;
  background: linear-gradient(135deg, #F3AF27, #FFD253);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #554F4C;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0;
  box-shadow: 0 2px 8px rgba(243, 175, 39, 0.4);
}

.brand-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.new-session-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 14px;
  background: linear-gradient(135deg, #F3AF27, #FFD253);
  color: #554F4C;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(243, 175, 39, 0.3);
}

.new-session-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(243, 175, 39, 0.5);
}

.new-session-btn:active {
  transform: translateY(0);
}

.btn-icon {
  font-size: 18px;
  line-height: 1;
}

.session-section-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--text-muted);
  padding: 8px 14px 4px;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-list::-webkit-scrollbar {
  width: 4px;
}

.session-list::-webkit-scrollbar-track {
  background: transparent;
}

.session-list::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 4px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-secondary);
  transition: all 0.15s;
  white-space: nowrap;
  overflow: hidden;
}

.session-item:hover {
  background-color: var(--accent-light);
  color: var(--text-primary);
}

.session-item.active {
  background-color: var(--accent-light);
  color: var(--accent);
  font-weight: 600;
}

.session-icon {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  opacity: 0.6;
}

.theme-icon {
  display: flex;
  align-items: center;
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-footer {
  border-top: 1px solid var(--border);
  padding-top: 12px;
}

.theme-toggle-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 14px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.theme-toggle-btn:hover {
  background-color: var(--accent-light);
  color: var(--accent);
  border-color: var(--accent);
}

/* ===== 主聊天区 ===== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--chat-bg);
  overflow: hidden;
  transition: background-color 0.3s;
}

/* ===== 顶部标题栏 ===== */
.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  background-color: var(--chat-bg);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-avatar {
  width: 38px;
  height: 38px;
  background: linear-gradient(135deg, #F3AF27, #FFD253);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #554F4C;
  font-size: 17px;
  box-shadow: 0 2px 8px rgba(243, 175, 39, 0.35);
}

.header-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.header-status {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-muted);
}

.status-dot {
  width: 7px;
  height: 7px;
  background: #F3AF27;
  border-radius: 50%;
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {

  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.4;
  }
}

/* ===== 消息列表 ===== */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  scroll-behavior: smooth;
}

.message-list::-webkit-scrollbar {
  width: 5px;
}

.message-list::-webkit-scrollbar-track {
  background: transparent;
}

.message-list::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 4px;
}

/* ===== 消息行 ===== */
.message-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  animation: msg-in 0.25s ease-out;
  max-width: 80%;
}

@keyframes msg-in {
  from {
    opacity: 0;
    transform: translateY(12px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-row.user {
  flex-direction: row-reverse;
  margin-left: auto;
}

.message-row.assistant {
  margin-right: auto;
}

/* ===== 头像 ===== */
.avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}

.assistant-avatar {
  background: linear-gradient(135deg, #F3AF27, #FFD253);
  color: #554F4C;
  box-shadow: 0 2px 8px rgba(243, 175, 39, 0.3);
}

.user-avatar {
  background: linear-gradient(135deg, #CF9267, #E9BE91);
  color: #554F4C;
  box-shadow: 0 2px 8px rgba(207, 146, 103, 0.35);
  font-size: 12px;
}

/* ===== 气泡 ===== */
.bubble-wrapper {
  display: flex;
  flex-direction: column;
  max-width: 100%;
}

.thinking-context {
  margin-bottom: 8px;
  padding: 8px 12px;
  border: 1px dashed var(--border);
  border-radius: 10px;
  background-color: var(--accent-light);
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 15px;
  line-height: 1.65;
  word-wrap: break-word;
  white-space: pre-wrap;
  box-shadow: var(--shadow-sm);
}

.message-row.user .message-bubble {
  background: linear-gradient(135deg, #F3AF27, #FFD253);
  color: #554F4C;
  border-bottom-right-radius: 4px;
}

.message-row.assistant .message-bubble {
  background-color: var(--ai-bubble);
  color: var(--ai-bubble-text);
  border-bottom-left-radius: 4px;
  border: 1px solid var(--border);
}

/* ===== Markdown 渲染样式 ===== */
.message-bubble.markdown-body {
  white-space: normal;
}

.message-bubble.markdown-body :deep(p) {
  margin: 0 0 0.6em;
}

.message-bubble.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.message-bubble.markdown-body :deep(h1),
.message-bubble.markdown-body :deep(h2),
.message-bubble.markdown-body :deep(h3),
.message-bubble.markdown-body :deep(h4) {
  margin: 0.8em 0 0.4em;
  font-weight: 600;
  line-height: 1.3;
}

.message-bubble.markdown-body :deep(ul),
.message-bubble.markdown-body :deep(ol) {
  margin: 0.4em 0 0.6em;
  padding-left: 1.4em;
}

.message-bubble.markdown-body :deep(li) {
  margin-bottom: 0.25em;
}

.message-bubble.markdown-body :deep(code) {
  font-family: 'Fira Code', 'Cascadia Code', Consolas, monospace;
  font-size: 0.875em;
  padding: 0.15em 0.4em;
  border-radius: 4px;
  background-color: rgba(0, 0, 0, 0.06);
}

.message-bubble.markdown-body :deep(pre) {
  margin: 0.6em 0;
  border-radius: 8px;
  overflow-x: auto;
  background-color: #1e1e2e;
}

.message-bubble.markdown-body :deep(pre code) {
  display: block;
  padding: 1em;
  background: transparent;
  color: #cdd6f4;
  font-size: 0.85em;
  line-height: 1.6;
  white-space: pre;
}

.message-bubble.markdown-body :deep(blockquote) {
  margin: 0.5em 0;
  padding: 0.4em 0.8em;
  border-left: 3px solid var(--accent);
  background-color: var(--accent-light);
  border-radius: 0 4px 4px 0;
  color: var(--text-secondary);
}

.message-bubble.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.6em 0;
  font-size: 0.9em;
}

.message-bubble.markdown-body :deep(th),
.message-bubble.markdown-body :deep(td) {
  border: 1px solid var(--border);
  padding: 6px 10px;
  text-align: left;
}

.message-bubble.markdown-body :deep(th) {
  background-color: var(--accent-light);
  font-weight: 600;
}

.message-bubble.markdown-body :deep(a) {
  color: var(--accent-hover);
  text-decoration: underline;
}

.message-bubble.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--border);
  margin: 0.8em 0;
}

.message-bubble.markdown-body :deep(strong) {
  font-weight: 700;
}

.message-bubble.markdown-body :deep(em) {
  font-style: italic;
}

/* ===== 加载气泡 ===== */
.loading-bubble {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 14px 18px;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background-color: var(--text-muted);
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}

.dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {

  0%,
  80%,
  100% {
    transform: scale(0.6);
    opacity: 0.4;
  }

  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* ===== 输入区 ===== */
.input-wrapper {
  padding: 16px 20px 20px;
  border-top: 1px solid var(--border);
  background-color: var(--chat-bg);
}

.input-box {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background-color: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: 14px;
  padding: 10px 12px;
  box-shadow: var(--shadow-sm);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input-box:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(243, 175, 39, 0.2);
}

.deep-think-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.2s;
  align-self: flex-end;
  margin-bottom: 2px;
}

.deep-think-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  background-color: var(--accent-light);
}

.deep-think-btn.active {
  background-color: var(--accent);
  color: #554F4C;
  border-color: var(--accent);
  box-shadow: 0 2px 8px rgba(243, 175, 39, 0.35);
}

.btn-label {
  font-size: 12px;
}

textarea {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 15px;
  font-family: var(--font);
  line-height: 1.6;
  resize: none;
  min-height: 24px;
  max-height: 160px;
  overflow-y: auto;
  padding: 4px 0;
}

textarea::placeholder {
  color: var(--text-muted);
}

.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #F3AF27, #FFD253);
  color: #554F4C;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(243, 175, 39, 0.35);
  align-self: flex-end;
}

.send-btn svg {
  width: 16px;
  height: 16px;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(243, 175, 39, 0.5);
}

.send-btn:disabled {
  background: var(--border);
  box-shadow: none;
  cursor: not-allowed;
  color: var(--text-muted);
}

.input-hint {
  text-align: center;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 8px;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .sidebar {
    display: none;
  }

  .message-row {
    max-width: 90%;
  }
}
</style>