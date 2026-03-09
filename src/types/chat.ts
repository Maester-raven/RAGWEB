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

/** 新增：对话记录（ChatRecord）类型（按你的业务调整字段）*/
export interface ChatRecord {
  id: string;          // 记录ID
  title?: string;      // 对话标题（可选）
  createTime: number;  // 创建时间戳
  messages: Message[]; // 该记录下的所有消息
  // 其他你需要的字段...
}