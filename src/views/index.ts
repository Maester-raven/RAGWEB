// 原有类型保留，新增：
export interface ChatRecord {
  user_id?: string;       // 可选，默认default_user
  session_id: string;     // 必选，会话ID
  role: 'user' | 'assistant'; // 必选，角色
  content: string;        // 必选，消息内容
}

// （可选）AI响应类型补充（如果需要）
export interface AiResponse {
  id: string;
  content: string;
}