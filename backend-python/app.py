from __future__ import annotations

import atexit
import os
import threading
from datetime import datetime
from ipaddress import ip_address
from typing import Any, cast

from flask import Flask, jsonify, request
import pymysql  # type: ignore[import-not-found]

try:
    import ip2region.searcher as ip2xdb  # type: ignore[import-not-found]
    import ip2region.util as ip2util  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    ip2xdb = None
    ip2util = None

app = Flask(__name__)

def load_env_file() -> None:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)

load_env_file()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_DATABASE = os.getenv("DB_DATABASE", "ragweb")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "9000"))

IP2REGION_DB_PATH = os.getenv(
    "IP2REGION_DB_PATH",
    os.path.join(os.path.dirname(__file__), "ip2region", "ip2region_v4.xdb"),
)

_schema_ready = False
_schema_lock = threading.Lock()
_searcher = None


def json_resp(status: int, data: dict[str, Any]):
    return jsonify(data), status


def get_conn() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_DATABASE,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def ensure_column_exists(
    cursor: pymysql.cursors.Cursor,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    exists = cast(dict[str, Any] | None, cursor.fetchone())
    if exists:
        return

    cursor.execute(
        f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {column_definition}"
    )


def ensure_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        conn = get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chat_users (
                        id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(64) NOT NULL UNIQUE,
                        ip VARCHAR(45) NULL,
                        region VARCHAR(255) NULL,
                        create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                ensure_column_exists(cursor, "chat_users", "ip", "VARCHAR(45) NULL")
                ensure_column_exists(cursor, "chat_users", "region", "VARCHAR(255) NULL")
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT UNSIGNED NOT NULL,
                        session_id VARCHAR(64) NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_session_time (user_id, session_id, create_time),
                        CONSTRAINT fk_chat_sessions_user
                          FOREIGN KEY (user_id) REFERENCES chat_users(id)
                          ON UPDATE CASCADE ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
            conn.commit()
            _schema_ready = True
        finally:
            conn.close()


def _build_ip2region_searcher():
    if ip2xdb is None or ip2util is None:
        return None
    if not os.path.exists(IP2REGION_DB_PATH):
        app.logger.warning("ip2region xdb 文件不存在: %s", IP2REGION_DB_PATH)
        return None

    try:
        ip2util.verify_from_file(IP2REGION_DB_PATH)
        with open(IP2REGION_DB_PATH, "rb") as handle:
            header = ip2util.load_header(handle)
            version = ip2util.version_from_header(header)
            if version is None:
                raise RuntimeError("无法从 xdb header 解析 IP 版本")
            v_index = ip2util.load_vector_index(handle)
        return ip2xdb.new_with_vector_index(version, IP2REGION_DB_PATH, v_index)
    except Exception as exc:  # pragma: no cover
        app.logger.warning("初始化 ip2region 失败，将使用 Unknown: %s", exc)
        return None


def _close_searcher() -> None:
    if _searcher is None:
        return
    try:
        _searcher.close()
    except Exception:
        pass


def extract_client_ip() -> str:
    xff = request.headers.get("X-Forwarded-For", "").strip()
    if xff:
        return xff.split(",")[0].strip()

    xri = request.headers.get("X-Real-IP", "").strip()
    if xri:
        return xri

    return (request.remote_addr or "").strip() or "0.0.0.0"


def normalize_ip(raw_ip: str) -> str:
    if not raw_ip:
        return "0.0.0.0"
    ip = raw_ip.strip()
    if ip.startswith("::ffff:"):
        ip = ip[7:]
    if "%" in ip:
        ip = ip.split("%", 1)[0]
    return ip


def lookup_region(raw_ip: str) -> tuple[str, str]:
    ip = normalize_ip(raw_ip)
    try:
        ip_address(ip)
    except ValueError:
        return ip, "Unknown"

    if _searcher is None:
        return ip, "Unknown"

    try:
        region = _searcher.search(ip)
        return ip, (region or "Unknown")
    except Exception:
        return ip, "Unknown"


def ensure_user_id_by_username(conn: pymysql.connections.Connection, username_raw: str, client_ip: str) -> int:
    username = (username_raw or "").strip() or "default_user"
    ip, region = lookup_region(client_ip)

    with conn.cursor() as cursor:
        # 仅在首次插入用户时落库 IP 与地区；已存在用户不会被覆盖。
        cursor.execute(
            """
            INSERT INTO chat_users (username, ip, region)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)
            """,
            (username, ip, region),
        )
        cursor.execute("SELECT LAST_INSERT_ID() AS id")
        row = cast(dict[str, Any] | None, cursor.fetchone())

    user_id = int((row or {}).get("id") or 0)
    if user_id <= 0:
        raise RuntimeError("用户创建或查询失败")
    return user_id


def _to_str_time(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


@app.route("/", methods=["GET"])
def health_check():
    return json_resp(200, {"code": 200, "message": "ok", "data": {"service": "chat-python-backend"}})


@app.route("/api/chat/record", methods=["POST"])
def save_record():
    ensure_schema()
    body = request.get_json(silent=True) or {}

    username = str(body.get("user_id") or "default_user")
    session_id = str(body.get("session_id") or "").strip()
    question = str(body.get("question") or "").strip()
    answer = str(body.get("answer") or "").strip()

    if not session_id or not question or not answer:
        return json_resp(400, {"code": 400, "message": "缺少必要字段：session_id/question/answer"})

    conn = get_conn()
    try:
        user_id = ensure_user_id_by_username(conn, username, extract_client_ip())
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO chat_sessions (user_id, session_id, question, answer) VALUES (%s, %s, %s, %s)",
                (user_id, session_id, question, answer),
            )
            insert_id = cursor.lastrowid
        conn.commit()
        return json_resp(200, {"code": 200, "message": "保存成功", "data": {"id": insert_id}})
    except Exception as exc:
        conn.rollback()
        return json_resp(500, {"code": 500, "message": "服务器错误", "error": str(exc)})
    finally:
        conn.close()


@app.route("/api/chat/records/<path:session_id>", methods=["GET", "DELETE"])
def records(session_id: str):
    ensure_schema()
    username = (request.args.get("user_id") or "default_user").strip() or "default_user"

    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM chat_users WHERE username = %s LIMIT 1", (username,))
            user = cast(dict[str, Any], cursor.fetchone() or {})
            user_id = user.get("id")

            if request.method == "GET":
                if not user_id:
                    return json_resp(200, {"code": 200, "message": "获取成功", "data": []})

                cursor.execute(
                    """
                    SELECT id, question, answer, create_time
                    FROM chat_sessions
                    WHERE session_id = %s AND user_id = %s
                    ORDER BY create_time ASC, id ASC
                    """,
                    (session_id, user_id),
                )
                turns = cast(list[dict[str, Any]], cursor.fetchall() or [])

                messages = []
                for turn in turns:
                    cid = turn["id"]
                    ctime = _to_str_time(turn.get("create_time"))
                    messages.append(
                        {
                            "id": f"{cid}-u",
                            "role": "user",
                            "content": turn.get("question", ""),
                            "create_time": ctime,
                        }
                    )
                    messages.append(
                        {
                            "id": f"{cid}-a",
                            "role": "assistant",
                            "content": turn.get("answer", ""),
                            "create_time": ctime,
                        }
                    )

                return json_resp(200, {"code": 200, "message": "获取成功", "data": messages})

            if not user_id:
                return json_resp(200, {"code": 200, "message": "删除成功", "data": {"affectedRows": 0}})

            cursor.execute(
                "DELETE FROM chat_sessions WHERE session_id = %s AND user_id = %s",
                (session_id, user_id),
            )
            affected = cursor.rowcount
        conn.commit()
        return json_resp(200, {"code": 200, "message": "删除成功", "data": {"affectedRows": affected}})
    except Exception as exc:
        conn.rollback()
        return json_resp(500, {"code": 500, "message": "服务器错误", "error": str(exc)})
    finally:
        conn.close()


@app.route("/api/chat/sessions/<path:user_id>", methods=["GET"])
def sessions(user_id: str):
    ensure_schema()

    conn = get_conn()
    try:
        uid = ensure_user_id_by_username(conn, user_id, extract_client_ip())
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT cs.session_id,
                       MAX(cs.create_time) AS last_time,
                       MIN(cs.create_time) AS create_time,
                       (SELECT question FROM chat_sessions
                        WHERE session_id = cs.session_id AND user_id = cs.user_id
                        ORDER BY create_time ASC, id ASC LIMIT 1) AS first_message
                FROM chat_sessions cs
                WHERE cs.user_id = %s
                GROUP BY cs.session_id, cs.user_id
                ORDER BY last_time DESC
                """,
                (uid,),
            )
            rows = cast(list[dict[str, Any]], cursor.fetchall() or [])

        data = []
        for row in rows:
            data.append(
                {
                    "session_id": row.get("session_id"),
                    "last_time": _to_str_time(row.get("last_time")),
                    "create_time": _to_str_time(row.get("create_time")),
                    "first_message": row.get("first_message"),
                }
            )

        conn.commit()
        return json_resp(200, {"code": 200, "message": "获取成功", "data": data})
    except Exception as exc:
        conn.rollback()
        return json_resp(500, {"code": 500, "message": "服务器错误", "error": str(exc)})
    finally:
        conn.close()


if __name__ == "__main__":
    ensure_schema()
    _searcher = _build_ip2region_searcher()
    atexit.register(_close_searcher)
    app.run(host=APP_HOST, port=APP_PORT)
