import axios from 'axios'
import type { ChatRequest, ChatResponse } from '../types'

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