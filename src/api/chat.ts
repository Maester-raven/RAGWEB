import axios from 'axios'
import type { ChatRequest, ChatResponse, ChatRecord } from '../types/chat' // 修正导入路径

const CHAT_TIMEOUT_MS = Number(import.meta.env.VITE_CHAT_TIMEOUT_MS ?? 15000)

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: CHAT_TIMEOUT_MS,
})

const CONTEXT_OVERFLOW_CODE = 'CONTEXT_OVERFLOW'
const CONTEXT_OVERFLOW_FALLBACK_MESSAGE = '输入内容过长，已超过模型上下文长度上限，请精简后重试。'

const extractErrorDetailFromAny = (payload: unknown): string => {
  if (!payload) return ''
  if (typeof payload === 'string') return payload
  if (typeof payload !== 'object') return ''

  const record = payload as Record<string, unknown>
  const candidate = record.detail ?? record.message ?? record.error ?? record.msg
  if (typeof candidate === 'string') return candidate

  if (Array.isArray(candidate)) {
    return candidate
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object') {
          const itemRecord = item as Record<string, unknown>
          return String(itemRecord.msg ?? itemRecord.message ?? itemRecord.detail ?? '')
        }
        return ''
      })
      .filter(Boolean)
      .join('; ')
  }

  return ''
}

const extractErrorCodeFromAny = (payload: unknown): string => {
  if (!payload || typeof payload !== 'object') return ''

  const record = payload as Record<string, unknown>
  const candidate = record.code ?? record.error_code ?? record.errorCode

  if (typeof candidate === 'string') return candidate
  if (typeof candidate === 'number') return String(candidate)
  return ''
}

const normalizeApiErrorDetail = (payload: unknown, fallbackDetail = ''): string => {
  const detail = extractErrorDetailFromAny(payload) || fallbackDetail
  const code = extractErrorCodeFromAny(payload).toUpperCase()

  if (code === CONTEXT_OVERFLOW_CODE) {
    return detail || CONTEXT_OVERFLOW_FALLBACK_MESSAGE
  }

  return detail
}

const extractApiErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const responseData = error.response?.data
    const detail = normalizeApiErrorDetail(responseData)
    if (detail) return detail
    if (typeof error.message === 'string' && error.message) return error.message
    return '请求失败'
  }

  if (error instanceof Error) return error.message
  return String(error)
}

export const sendMessage = async (data: ChatRequest): Promise<ChatResponse> => {
  try {
    const response = await api.post<ChatResponse>('/v1/rag/chat', data)
    return response.data
  } catch (error) {
    throw new Error(extractApiErrorMessage(error))
  }
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
  const controller = new AbortController()
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  const refreshTimeout = () => {
    if (timeoutId) clearTimeout(timeoutId)
    timeoutId = setTimeout(() => {
      controller.abort()
    }, CHAT_TIMEOUT_MS)
  }

  try {
    refreshTimeout()
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/v1/rag/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...data, stream: true }),
      signal: controller.signal,
    })

    if (!response.ok) {
      const rawText = await response.text()
      let detail = rawText
      let parsedPayload: unknown = null

      try {
        parsedPayload = rawText ? JSON.parse(rawText) : null
      } catch {
        // 非 JSON 响应，保留原始文本
      }

      if (parsedPayload) {
        detail = normalizeApiErrorDetail(parsedPayload, detail)
      } else if (/CONTEXT_OVERFLOW/i.test(rawText)) {
        detail = CONTEXT_OVERFLOW_FALLBACK_MESSAGE
      }

      const suffix = detail || response.statusText || '请求失败'
      throw new Error(`HTTP ${response.status}: ${suffix}`)
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('ReadableStream 不可用')

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      refreshTimeout()
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
    if (error instanceof DOMException && error.name === 'AbortError') {
      onError(new Error(`请求超时，请在网络稳定后重试（>${CHAT_TIMEOUT_MS}ms）`))
      return
    }
    onError(error as Error)
  } finally {
    if (timeoutId) clearTimeout(timeoutId)
  }
}

// ========== 数据库相关接口（新增，无原有逻辑改动） ==========
// 创建数据库接口专用的axios实例（避免影响原有/v1接口）
const chatDbApi = axios.create({
  baseURL: '/api/chat', // 配合vite proxy转发到localhost:3000/chat
  timeout: 10000,
})

/**
 * 保存一轮对话到数据库
 * @param data 对话轮次（session_id/question/answer 必填）
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

/**
 * 获取用户的所有会话列表
 * @param user_id 用户ID
 */
export const getSessionsList = async (user_id: string) => {
  return chatDbApi.get(`/sessions/${encodeURIComponent(user_id)}`)
}

