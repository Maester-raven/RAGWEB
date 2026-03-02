<template>
  <div class="chat-container" :class="{ 'dark-theme': chatStore.isDarkTheme }">
    <!-- 左侧对话历史栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>对话历史</h2>
        <button class="new-session-btn" @click="chatStore.createNewSession()">+ 新对话</button>
      </div>
      <div class="session-list">
        <div
          v-for="session in chatStore.sessions"
          :key="session.id"
          :class="['session-item', { active: session.id === chatStore.currentSessionId }]"
          @click="chatStore.switchSession(session.id)"
        >
          {{ session.title }}
        </div>
      </div>
    </aside>

    <!-- 中间聊天区 -->
    <main class="chat-main">
      <!-- 顶部工具栏 - 移除深度思考按钮 -->
      <div class="chat-header">
        <div class="header-buttons">
          <!-- 修改2：移除按钮上的图标 -->
          <button class="theme-toggle-btn" @click="chatStore.toggleTheme()">
            {{ chatStore.isDarkTheme ? '浅色' : '深色' }}
          </button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="message-list">
        <div
          v-for="message in chatStore.messages"
          :key="message.id"
          :class="['message', message.role]"
        >
          <div class="message-content">{{ message.content }}</div>
        </div>
        <div v-if="chatStore.isLoading" class="loading">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </div>

      <!-- 输入区 - 新增深度思考按钮 -->
      <div class="input-area">
        <textarea
          v-model="inputText"
          placeholder="输入你的问题..."
          @keydown.enter.prevent="handleSend"
        ></textarea>
        <!-- 修改3：将深度思考按钮移到输入区，移除图标 -->
        <div class="input-actions">
          <button
            class="deep-think-btn"
            :class="{ active: chatStore.isDeepThinking }"
            @click="chatStore.toggleDeepThinking()"
          >
            深度思考
          </button>
          <button @click="handleSend" :disabled="!inputText.trim() || chatStore.isLoading">
            发送
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useChatStore } from '../store/chat'
import { sendMessage } from '../api/chat'
import type { Message, ChatRequest } from '../types'

const chatStore = useChatStore()
const inputText = ref('')

const handleSend = async () => {
  if (!inputText.value.trim() || chatStore.isLoading) return

  const userMessage: Message = {
    id: Date.now().toString(),
    content: inputText.value,
    role: 'user',
    timestamp: Date.now(),
  }

  chatStore.addMessage(userMessage)
  chatStore.setLoading(true)

  try {
    const requestData: ChatRequest & { deepThinking?: boolean } = {
      messages: chatStore.messages,
      ...(chatStore.isDeepThinking && { deepThinking: true }),
    }

    const response = await sendMessage(requestData)

    const assistantMessage: Message = {
      id: response.id,
      content: response.content,
      role: 'assistant',
      timestamp: Date.now(),
    }

    chatStore.addMessage(assistantMessage)
  } catch (error) {
    console.error('发送消息失败:', error)
    chatStore.addMessage({
      id: Date.now().toString(),
      content: '抱歉，发送失败了，请稍后再试。',
      role: 'assistant',
      timestamp: Date.now(),
    })
  } finally {
    chatStore.setLoading(false)
    inputText.value = ''
  }
}

onMounted(() => {
  if (chatStore.messages.length === 0) {
    chatStore.addMessage({
      id: 'welcome',
      content: '你好！我是AI助手，有什么可以帮助你的吗？',
      role: 'assistant',
      timestamp: Date.now(),
    })
  }
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
/* 全局变量定义 - 优化字体相关变量 */
/* 全局变量定义 */
:root {
  --bg-color: #f5f5f5;
  --sidebar-bg: #ffffff;
  --chat-bg: #ffffff;
  --text-color: #333333;
  --message-user-bg: #007aff;
  --message-user-text: #ffffff;
  --message-assistant-bg: #e5e5ea;
  --message-assistant-text: #000000;
  --input-bg: #ffffff;
  /* 修改这里：将浅色模式下的分割线颜色从浅灰改为深黑 */
  --input-border: #000000; 
  --button-bg: #007aff;
  --button-text: #ffffff;
  --hover-bg: #f0f0f0;
  /* 字体美化变量保持不变 */
  --font-main: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --font-size-base: 15px;
  --font-size-sm: 14px;
  --font-size-lg: 16px;
  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --line-height-base: 1.6;
}

.dark-theme {
  --bg-color: #1a1a1a;
  --sidebar-bg: #2d2d2d;
  --chat-bg: #1e1e1e;
  --text-color: #e0e0e0;
  --message-user-bg: #0a84ff;
  --message-user-text: #ffffff;
  --message-assistant-bg: #2d3748;
  --message-assistant-text: #e0e0e0;
  --input-bg: #2d2d2d;
  --input-border: #4a4a4a; /* 深色模式下的分割线颜色保持不变 */
  --button-bg: #0a84ff;
  --button-text: #ffffff;
  --hover-bg: #3a3a3a;
}

/* 整体布局 - 应用字体美化 */
.chat-container {
  display: flex;
  height: 100vh;
  background-color: var(--bg-color);
  color: var(--text-color);
  transition: all 0.3s ease;
  font-family: var(--font-main);
  font-size: var(--font-size-base);
  line-height: var(--line-height-base);
  font-weight: var(--font-weight-regular);
}

/* 左侧边栏 - 字体优化 */
.sidebar {
  width: 280px;
  background-color: var(--sidebar-bg);
  border-right: 1px solid var(--input-border);
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid var(--input-border);
}

.sidebar-header h2 {
  margin: 0 0 16px 0;
  font-size: 18px;
  font-weight: var(--font-weight-semibold);
}

.new-session-btn {
  width: 100%;
  padding: 10px;
  background-color: var(--button-bg);
  color: var(--button-text);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  transition: background-color 0.2s;
}

.new-session-btn:hover {
  background-color: #0056cc;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.session-item {
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-regular);
}

.session-item:hover {
  background-color: var(--hover-bg);
}

.session-item.active {
  background-color: var(--button-bg);
  color: var(--button-text);
}

/* 中间聊天区 - 字体优化 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--chat-bg);
  transition: all 0.3s ease;
}

.chat-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--input-border);
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.header-buttons {
  display: flex;
  gap: 12px;
}

.theme-toggle-btn,
.deep-think-btn {
  padding: 8px 16px;
  border: 1px solid var(--input-border);
  border-radius: 8px;
  background-color: var(--input-bg);
  color: var(--text-color);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  transition: all 0.2s;
}

.theme-toggle-btn:hover,
.deep-think-btn:hover {
  background-color: var(--hover-bg);
}

.deep-think-btn.active {
  background-color: var(--button-bg);
  color: var(--button-text);
  border-color: var(--button-bg);
}

/* 消息列表 - 字体优化 */
.message-list {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.message {
  margin-bottom: 16px;
  max-width: 70%;
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user {
  margin-left: auto;
  text-align: right;
}

.message.assistant {
  margin-right: auto;
}

.message-content {
  padding: 12px 16px;
  border-radius: 18px;
  display: inline-block;
  word-wrap: break-word;
  white-space: pre-wrap;
  line-height: var(--line-height-base);
  font-size: var(--font-size-base);
}

.message.user .message-content {
  background-color: var(--message-user-bg);
  color: var(--message-user-text);
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  background-color: var(--message-assistant-bg);
  color: var(--message-assistant-text);
  border-bottom-left-radius: 4px;
}

.loading {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background-color: var(--message-assistant-bg);
  border-radius: 18px;
  border-bottom-left-radius: 4px;
  width: fit-content;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--text-color);
  opacity: 0.6;
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* 输入区 - 重构布局，适配深度思考按钮 */
.input-area {
  display: flex;
  padding: 16px 20px;
  border-top: 1px solid var(--input-border);
  background-color: var(--chat-bg);
  gap: 12px;
  align-items: flex-end;
}

textarea {
  flex: 1;
  padding: 12px;
  border: 1px solid var(--input-border);
  border-radius: 8px;
  resize: none;
  font-size: var(--font-size-lg);
  background-color: var(--input-bg);
  color: var(--text-color);
  transition: border-color 0.2s;
  line-height: var(--line-height-base);
  font-family: var(--font-main);
  min-height: 60px;
}

textarea:focus {
  outline: none;
  border-color: var(--button-bg);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
}

/* 输入区按钮组 */
.input-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-actions button {
  margin-left: 0;
  padding: 12px 24px;
  background-color: var(--button-bg);
  color: var(--button-text);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-medium);
  transition: background-color 0.2s;
  width: 100%;
}

button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

button:hover:not(:disabled) {
  background-color: #0056cc;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    width: 0;
    overflow: hidden;
  }

  .chat-main {
    flex: 1;
  }

  .input-actions {
    flex-direction: row;
  }
}
</style>