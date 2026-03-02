export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: number
}

export interface ChatRequest {
  messages: Message[]
  model?: string
}

export interface ChatResponse {
  id: string
  content: string
  role: 'assistant'
}