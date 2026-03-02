import axios from 'axios'
import type { ChatRequest, ChatResponse } from '../types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 60000,
})

export const sendMessage = async (data: ChatRequest & { deepThinking?: boolean }): Promise<ChatResponse> => {
  const response = await api.post<ChatResponse>('/chat', data)
  return response.data
}