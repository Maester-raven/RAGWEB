<template>
  <div class="settings-container">
    <h1>设置</h1>
    <div class="setting-item">
      <label>API 地址</label>
      <input v-model="apiUrl" type="text" placeholder="http://localhost:8000/api" />
    </div>
    <div class="setting-item">
      <label>模型选择</label>
      <select v-model="selectedModel">
        <option value="gpt-3.5-turbo">GPT-3.5-turbo</option>
        <option value="gpt-4">GPT-4</option>
      </select>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const apiUrl = ref(import.meta.env.VITE_API_BASE_URL)
const selectedModel = ref('gpt-3.5-turbo')
</script>

<style scoped>
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

label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
}

input, select {
  width: 100%;
  padding: 10px;
  border: 1px solid #e5e5ea;
  border-radius: 4px;
}
</style>