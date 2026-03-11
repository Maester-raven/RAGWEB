# RAGWEB

RAGWEB 是一个基于 **RAG（检索增强生成）** 的全栈 AI 对话 Web 应用。前端采用 Vue 3 + TypeScript + Vite 构建，后端使用 Node.js + Express，聊天记录持久化存储于 MySQL 数据库，并通过调用外部 RAG API 服务实现智能问答。

## 功能特性

- **AI 对话**：接入外部 RAG API，支持上下文感知的多轮对话
- **流式输出**：基于 SSE/ReadableStream，AI 回复逐字实时渲染
- **深度思考模式**：支持 Qwen3 等具备 `<think>` 标签的推理模型，可展示/隐藏思考过程
- **多会话管理**：支持创建新会话、切换会话，自动以首条消息为会话标题
- **历史记录持久化**：对话记录通过后端接口存入 MySQL，支持按会话查询与删除
- **Markdown 渲染**：AI 回复内容通过 marked + DOMPurify 安全渲染为富文本
- **深色 / 浅色主题**：一键切换，状态全局同步
- **语音输入**：集成 RecordRTC，支持麦克风录音输入
- **设置页**：可动态配置 API 地址、模型选择、流式输出开关

## 技术栈

| 层级          | 技术                           |
| ------------- | ------------------------------ |
| 前端框架      | Vue 3 + TypeScript             |
| 构建工具      | Vite 7                         |
| 状态管理      | Pinia                          |
| 路由          | Vue Router 4                   |
| HTTP 客户端   | Axios + Fetch API（流式）      |
| Markdown 渲染 | marked + DOMPurify             |
| 语音录制      | RecordRTC                      |
| 后端框架      | Node.js + Express              |
| 数据库        | MySQL（mysql2/promise 连接池） |

## 项目结构

```
RAGWEB/
├── backend/                # 后端（Node.js + Express）
│   ├── app.js              # 服务入口，注册路由与中间件
│   ├── package.json
│   └── db/
│       └── index.js        # MySQL 连接池配置
│   └── routes/
│       └── chat.js         # 聊天记录增删查接口
├── src/                    # 前端（Vue 3 + TypeScript）
│   ├── api/
│   │   └── chat.ts         # RAG API 调用 & 数据库接口封装
│   ├── assets/
│   │   └── main.css        # 全局样式
│   ├── router/
│   │   └── index.ts        # 前端路由配置
│   ├── store/
│   │   └── chat.ts         # Pinia 状态管理
│   ├── types/
│   │   └── chat.ts         # TypeScript 类型定义
│   ├── views/
│   │   ├── ChatView.vue    # 主聊天页面
│   │   └── SettingsView.vue# 设置页面
│   ├── App.vue
│   └── main.ts
├── .env                    # 环境变量（需手动创建，见下方说明）
├── vite.config.ts
└── package.json
```

## 快速开始

### 环境要求

- Node.js `^20.19.0` 或 `>=22.12.0`
- pnpm（前端包管理器）
- MySQL 数据库
- 已部署的 RAG API 服务（提供 `POST /v1/rag/chat` 接口）

### 1. 克隆项目

```sh
git clone https://github.com/yahayao/RAGWEB.git
cd RAGWEB
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
# RAG API 服务地址（前端直接调用）
VITE_API_BASE_URL=http://localhost:8000/api
```

在 `backend/` 目录创建 `.env` 文件：

```env
# MySQL 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_DATABASE=ragweb

# 后端监听端口（可选，默认 3000）
PORT=3000
```

### 3. 初始化数据库

在 MySQL 中执行以下 SQL 建表语句：

```sql
CREATE DATABASE IF NOT EXISTS ragweb;
USE ragweb;

CREATE TABLE IF NOT EXISTS chat_records (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     VARCHAR(64)  NOT NULL DEFAULT 'default_user',
  session_id  VARCHAR(64)  NOT NULL,
  role        VARCHAR(16)  NOT NULL COMMENT 'user | assistant',
  content     TEXT         NOT NULL,
  create_time DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 4. 安装依赖并启动

**前端：**

```sh
pnpm install
pnpm dev
```

前端默认运行在 `http://localhost:5173`。

**后端：**

```sh
cd backend
npm install
npm run dev
```

后端默认运行在 `http://localhost:3000`。

## 后端 API

| 方法     | 路径                            | 说明                   |
| -------- | ------------------------------- | ---------------------- |
| `POST`   | `/api/chat/record`              | 保存单条对话记录       |
| `GET`    | `/api/chat/records/:session_id` | 获取指定会话的历史记录 |
| `DELETE` | `/api/chat/records/:session_id` | 删除指定会话的所有记录 |
| `GET`    | `/`                             | 健康检查               |

## 构建生产版本

```sh
# 类型检查 + 构建前端
pnpm build

# 预览构建产物
pnpm preview
```

## 推荐开发工具

- [VS Code](https://code.visualstudio.com/) + [Vue - Official](https://marketplace.visualstudio.com/items?itemName=Vue.volar)（请禁用 Vetur）
- [Vue.js devtools（Chrome）](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
- [Vue.js devtools（Firefox）](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
