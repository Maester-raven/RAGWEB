<template>
  <div class="settings-container">
    <div class="settings-header">
      <h1>设置</h1>
      <button class="back-btn" @click="router.push('/')">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="16" height="16">
          <path d="M19 12H5M5 12L12 19M5 12L12 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"
            stroke-linejoin="round" />
        </svg>
        返回主页
      </button>
    </div>

    <div class="setting-item">
      <label>API 地址</label>
      <input v-model="apiUrl" type="text" placeholder="http://localhost:8000/api" />
    </div>

    <div class="setting-item">
      <label>模型选择</label>
      <select v-model="selectedModel">
        <option value="Qwen3-14B">Qwen3-14B</option>
        <option value="gpt-3.5-turbo">GPT-3.5-turbo</option>
        <option value="gpt-4">GPT-4</option>
      </select>
    </div>

    <!-- 流式输出开关 -->
    <div class="setting-item setting-item--row">
      <div class="setting-label-group">
        <label>流式输出</label>
        <span class="setting-desc">开启后 AI 回复将逐字实时显示</span>
      </div>
      <button class="toggle-btn" :class="{ 'toggle-btn--on': chatStore.isStreaming }"
        @click="chatStore.toggleStreaming()" :aria-label="chatStore.isStreaming ? '关闭流式输出' : '开启流式输出'">
        <span class="toggle-track">
          <span class="toggle-thumb"></span>
        </span>
        <span class="toggle-text">{{ chatStore.isStreaming ? '已开启' : '已关闭' }}</span>
      </button>
    </div>

    <div class="setting-item setting-item--row">
      <div class="setting-label-group">
        <label>显示思考内容</label>
        <span class="setting-desc">开启后可在聊天气泡上方查看思考内容</span>
      </div>
      <button class="toggle-btn" :class="{ 'toggle-btn--on': chatStore.isShowThinking }"
        @click="chatStore.toggleShowThinking()" :aria-label="chatStore.isShowThinking ? '关闭思考内容显示' : '开启思考内容显示'">
        <span class="toggle-track">
          <span class="toggle-thumb"></span>
        </span>
        <span class="toggle-text">{{ chatStore.isShowThinking ? '已开启' : '已关闭' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '../store/chat'

const router = useRouter()

const chatStore = useChatStore()

const apiUrl = ref(import.meta.env.VITE_API_BASE_URL)
const selectedModel = ref('gpt-3.5-turbo')
</script>

<style scoped>
.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.settings-header h1 {
  margin: 0;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid #e5e5ea;
  border-radius: 6px;
  background: #fff;
  color: #554f4c;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.back-btn:hover {
  background: #fef3cc;
  border-color: #f3af27;
  color: #554f4c;
}

.settings-container {
  max-width: 600px;
  margin: 40px auto;
  padding: 20px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.setting-item {
  margin-bottom: 20px;
}

.setting-item--row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.setting-label-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.setting-desc {
  font-size: 12px;
  color: #8b8b8b;
}

label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
}

.setting-item--row label {
  margin-bottom: 0;
}

input,
select {
  width: 100%;
  padding: 10px;
  border: 1px solid #e5e5ea;
  border-radius: 4px;
  box-sizing: border-box;
}

/* 开关按钮 */
.toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  flex-shrink: 0;
}

.toggle-track {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  border-radius: 12px;
  background-color: #d0d0d0;
  transition: background-color 0.25s;
}

.toggle-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background-color: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  transition: transform 0.25s;
}

.toggle-btn--on .toggle-track {
  background-color: #f3af27;
}

.toggle-btn--on .toggle-thumb {
  transform: translateX(20px);
}

.toggle-text {
  font-size: 14px;
  color: #554f4c;
  min-width: 42px;
}
</style>
