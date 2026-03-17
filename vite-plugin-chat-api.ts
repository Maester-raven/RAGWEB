import type { Connect, Plugin } from 'vite'
import type { IncomingMessage, ServerResponse } from 'node:http'
import { loadEnv } from 'vite'
import mysql from 'mysql2/promise'

function sendJson(res: ServerResponse, status: number, data: unknown) {
    res.writeHead(status, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(data))
}

function readBody(req: IncomingMessage): Promise<Record<string, unknown>> {
    return new Promise((resolve) => {
        let raw = ''
        req.on('data', (chunk: Buffer) => (raw += chunk.toString()))
        req.on('end', () => {
            try {
                resolve(JSON.parse(raw || '{}'))
            } catch {
                resolve({})
            }
        })
    })
}

export function chatApiPlugin(): Plugin {
    let pool: mysql.Pool | null = null

    const chatMiddleware: Connect.NextHandleFunction = async (
        req: IncomingMessage,
        res: ServerResponse,
        next: () => void,
    ) => {
        const rawUrl = req.url ?? ''
        if (!rawUrl.startsWith('/api/chat/')) return next()

        if (!pool) {
            return sendJson(res, 500, { code: 500, message: '数据库连接池未初始化，请检查 DB_* 环境变量' })
        }

        const urlObj = new URL(rawUrl, 'http://localhost')
        const pathname = urlObj.pathname
        const method = req.method ?? ''

        try {
            // POST /api/chat/record
            if (method === 'POST' && pathname === '/api/chat/record') {
                const body = await readBody(req)
                const user_id = (body.user_id as string) || 'default_user'
                const { session_id, role, content } = body as Record<string, string>
                const [result] = await pool.execute(
                    'INSERT INTO chat_records (user_id, session_id, role, content) VALUES (?, ?, ?, ?)',
                    [user_id, session_id, role, content],
                )
                const okResult = result as mysql.OkPacket
                return sendJson(res, 200, { code: 200, message: '保存成功', data: { id: okResult.insertId } })
            }

            // /api/chat/records/:session_id
            const recordsMatch = pathname.match(/^\/api\/chat\/records\/(.+)$/)
            if (recordsMatch) {
                const session_id = decodeURIComponent(recordsMatch[1])
                const user_id = urlObj.searchParams.get('user_id') ?? 'default_user'

                if (method === 'GET') {
                    const [rows] = await pool.execute(
                        'SELECT * FROM chat_records WHERE session_id = ? AND user_id = ? ORDER BY create_time ASC',
                        [session_id, user_id],
                    )
                    return sendJson(res, 200, { code: 200, message: '获取成功', data: rows })
                }

                if (method === 'DELETE') {
                    const [result] = await pool.execute(
                        'DELETE FROM chat_records WHERE session_id = ? AND user_id = ?',
                        [session_id, user_id],
                    )
                    const okResult = result as mysql.OkPacket
                    return sendJson(res, 200, { code: 200, message: '删除成功', data: { affectedRows: okResult.affectedRows } })
                }
            }

            // GET /api/chat/sessions/:user_id
            const sessionsMatch = pathname.match(/^\/api\/chat\/sessions\/(.+)$/)
            if (method === 'GET' && sessionsMatch) {
                const user_id = decodeURIComponent(sessionsMatch[1])
                const [rows] = await pool.execute(
                    `SELECT cr.session_id,
                      MAX(cr.create_time) AS last_time,
                      MIN(cr.create_time) AS create_time,
                      (SELECT content FROM chat_records
                       WHERE session_id = cr.session_id AND user_id = cr.user_id AND role = 'user'
                       ORDER BY create_time ASC LIMIT 1) AS first_message
               FROM chat_records cr
               WHERE cr.user_id = ?
               GROUP BY cr.session_id, cr.user_id
               ORDER BY last_time DESC`,
                    [user_id],
                )
                return sendJson(res, 200, { code: 200, message: '获取成功', data: rows })
            }
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : '未知错误'
            return sendJson(res, 500, { code: 500, message: '服务器错误', error: message })
        }

        next()
    }

    return {
        name: 'vite-plugin-chat-api',

        config(_, { mode }) {
            const env = loadEnv(mode, process.cwd(), '')
            pool = mysql.createPool({
                host: env.DB_HOST,
                port: Number(env.DB_PORT) || 3306,
                user: env.DB_USER,
                password: env.DB_PASSWORD,
                database: env.DB_DATABASE,
                waitForConnections: true,
                connectionLimit: 10,
                connectTimeout: 60000,
            })
        },

        configureServer(server) {
            server.middlewares.use(chatMiddleware)
        },

        configurePreviewServer(server) {
            server.middlewares.use(chatMiddleware)
        },
    }
}
