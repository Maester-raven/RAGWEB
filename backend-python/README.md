# Python Chat Backend

该目录是从 Vite 中间件拆分出来的独立 Python 后端，实现以下接口：

- `POST /api/chat/record`
- `GET /api/chat/records/:session_id`
- `DELETE /api/chat/records/:session_id`
- `GET /api/chat/sessions/:user_id`

并在用户首次写入 `chat_users` 时，使用 `ip2region` 将客户端 IP 对应地区存储到 `chat_users.ip` 与 `chat_users.region`。

## 1. 安装依赖

```bash
cd backend-python
pip install -r requirements.txt
```

## 2. 配置环境变量

可复制 `.env.example` 后按需修改，至少保证 MySQL 可访问。

注意：

- 需自行准备 `ip2region` 的 xdb 文件（例如 `ip2region_v4.xdb`）
- 默认路径是 `backend-python/ip2region/ip2region_v4.xdb`

## 3. 启动服务

```bash
uvicorn app:app --host 0.0.0.0 --port 9000
```

或直接：

```bash
python app.py
```

默认监听：`http://localhost:9000`

## 4. 与前端联调

根目录 `vite.config.ts` 已将 `/api/chat` 代理到 `VITE_CHAT_BACKEND_URL`（默认 `http://localhost:9000`）。
