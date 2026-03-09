import axios from 'axios'
import type { ChatRequest, ChatResponse, ChatRecord } from '../types/chat' // 修正导入路径

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 120000,
})

export const sendMessage = async (data: ChatRequest): Promise<ChatResponse> => {
  const response = await api.post<ChatResponse>('/v1/rag/chat', data)
  return response.data
}

/**
 * 流式发送消息（SSE / ReadableStream）
 * @param data       请求体（stream 字段会被强制设为 true）
 * @param onChunk    每收到一段内容时的回调
 * @param onDone     流结束时的回调
 * @param onError    发生错误时的回调
 */
export const sendMessageStream = async (
  data: ChatRequest,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (error: Error) => void,
): Promise<void> => {
  try {
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/v1/rag/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...data, stream: true }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('ReadableStream 不可用')

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data: ')) continue

        const payload = trimmed.slice(6)
        if (payload === '[DONE]') {
          onDone()
          return
        }

        try {
          const parsed = JSON.parse(payload)
          // 兼容标准 OpenAI delta 格式，也兼容直接返回 message.content 的格式
          const deltaContent: string | undefined =
            parsed.choices?.[0]?.delta?.content
            ?? parsed.choices?.[0]?.message?.content
          if (deltaContent) onChunk(deltaContent)
        } catch {
          // 忽略非 JSON 行
        }
      }
    }
    onDone()
  } catch (error) {
    onError(error as Error)
  }
}

// ========== 数据库相关接口（新增，无原有逻辑改动） ==========
// 创建数据库接口专用的axios实例（避免影响原有/v1接口）
const chatDbApi = axios.create({
  baseURL: '/api/chat', // 配合vite proxy转发到localhost:3000/chat
  timeout: 10000,
})

/**
 * 保存单条对话记录到数据库
 * @param data 对话记录（session_id/role/content 必填）
 */
export const saveChatRecord = async (data: ChatRecord) => {
  return chatDbApi.post('/record', data)
}

/**
 * 获取指定会话的历史对话记录
 * @param session_id 会话ID
 * @param user_id 可选：用户ID（默认default_user）
 */
export const getChatRecords = async (session_id: string, user_id?: string) => {
  return chatDbApi.get(`/records/${session_id}`, {
    params: { user_id }
  })
}

/**
 * 删除指定会话的所有对话记录
 * @param session_id 会话ID
 * @param user_id 可选：用户ID（默认default_user）
 */
export const deleteChatRecords = async (session_id: string, user_id?: string) => {
  return chatDbApi.delete(`/records/${session_id}`, {
    params: { user_id }
  })
}