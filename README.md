# RAGWEB

RAGWEB 是一个基于 **RAG（检索增强生成）** 的全栈 AI 对话 Web 应用。前端采用 Vue 3 + TypeScript + Vite 构建，后端使用独立 Python 服务，聊天记录持久化存储于 MySQL 数据库，并通过调用外部 RAG API 服务实现智能问答。

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
- **数据库持久化**：基于 PostgreSQL 存储用户、会话、聊天记录


## 技术栈

| 层级          | 技术                      |
| ------------- | ------------------------- |
| 前端框架      | Vue 3 + TypeScript        |
| 构建工具      | Vite 7                    |
| 状态管理      | Pinia                     |
| 路由          | Vue Router 4              |
| HTTP 客户端   | Axios + Fetch API（流式） |
| Markdown 渲染 | marked + DOMPurify        |
| 语音录制      | RecordRTC                 |
| 后端框架      | Python + Flask            |
| 数据库        | MySQL（PyMySQL）          |

## 项目结构

```
RAGWEB/
├── backend-python/         # 后端（Python + Flask）
│   ├── app.py              # 服务入口，注册聊天数据接口
│   ├── requirements.txt
│   └── ip2region/
│       └── ip2region_v4.xdb # 需自行准备（默认路径）
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

# 聊天记录后端（Python）地址，供 Vite 代理 /api/chat 使用
VITE_CHAT_BACKEND_URL=http://localhost:9000
```

在 `backend-python/` 目录创建环境变量（可参考 `.env.example`）：

```env
# MySQL 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_DATABASE=ragweb

# PostgreSQL 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=你的数据库密码
DB_DATABASE=ai_chat_db

# 后端监听端口（可选，默认 9000）
APP_PORT=9000

# ip2region xdb 文件路径
IP2REGION_DB_PATH=./ip2region/ip2region_v4.xdb
```

### 3. 初始化数据库

### 3. 初始化数据库
项目已内置 PostgreSQL 数据库脚本 `database.sql`，直接执行即可创建完整表结构：

1. 打开 pgAdmin 连接 PostgreSQL
2. 创建数据库 `ai_chat_db`
3. 执行项目根目录下的 `ai_chat_database.sql` 文件

在 MySQL 中执行以下 SQL 建表语句：

```sql
CREATE DATABASE IF NOT EXISTS ragweb;
USE ragweb;

CREATE TABLE IF NOT EXISTS chat_users (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  username    VARCHAR(64) NOT NULL UNIQUE,
  ip          VARCHAR(45) NULL,
  region      VARCHAR(255) NULL,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_sessions (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     BIGINT UNSIGNED  NOT NULL,
  session_id  VARCHAR(64)  NOT NULL,
  question    TEXT         NOT NULL,
  answer      TEXT         NOT NULL,
  create_time DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_session_time (user_id, session_id, create_time),
  CONSTRAINT fk_chat_sessions_user
    FOREIGN KEY (user_id) REFERENCES chat_users(id)
    ON UPDATE CASCADE ON DELETE CASCADE
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
cd backend-python
pip install -r requirements.txt
python app.py
```

后端默认运行在 `http://localhost:9000`。

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
