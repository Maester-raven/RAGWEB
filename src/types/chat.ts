// src/types/chat.ts
// 对话消息（前端展示用）
export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: number
}

/** 对话历史记录（传给后端的格式，不含前端内部字段）*/
export interface HistoryItem {
  role: 'user' | 'assistant'
  content: string
}

/** 手动传入的检索上下文 */
export interface RetrievedContext {
  content: string
  similarity?: number
  source?: string
}

/** POST /v1/rag/chat 请求体（和后端接口严格对齐）*/
export interface ChatRequest {
  question: string
  history?: HistoryItem[]
  contexts?: RetrievedContext[]
  similar_num?: number
  temperature?: number
  max_tokens?: number
  top_p?: number
  stream?: boolean
  enable_thinking?: boolean
  return_thinking?: boolean
  system_prompt_prefix?: string
}

/** POST /v1/rag/chat 响应体（和后端返回严格对齐）*/
export interface ChatResponse {
  id: string
  object: string
  created: number
  question: string
  context_count: number
  contexts: RetrievedContext[]
  choices: {
    index: number
    message: {
      role: 'assistant'
      content: string
    }
    finish_reason: string
  }[]
  usage: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}

/** 前端使用的会话聚合结构：一个会话下包含多条消息（Message[]） */
export interface ChatSession {
  id: string          // 会话ID
  title?: string      // 对话标题（可选）
  createTime: number  // 创建时间戳
  messages: Message[] // 该会话下的所有消息
}

/** 与后端保存/查询对话记录的数据库结构严格对齐：单条消息记录 */
export interface ChatRecord {
  user_id: string                   // 用户ID
  session_id: string                // 会话/对话ID
  role: 'user' | 'assistant'        // 角色
  content: string                   // 消息内容
}