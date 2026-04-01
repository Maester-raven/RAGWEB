from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from ipaddress import ip_address
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, create_engine, text
from sqlalchemy.orm import Mapped, Session, declarative_base, mapped_column, relationship, sessionmaker

try:
    import ip2region.searcher as ip2xdb  # type: ignore[import-not-found]
    import ip2region.util as ip2util  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    ip2xdb = None
    ip2util = None


logger = logging.getLogger(__name__)


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

# ====== 应用配置（可通过环境变量覆盖） ======
# PostgreSQL 连接地址，例如：postgresql://user:password@host:5432/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:123456@localhost:5432/ai_chat")

# HTTP 服务监听地址
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "9000"))

# SQLAlchemy 连接池配置
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))
DB_ECHO = os.getenv("DB_ECHO", "false").lower() in {"1", "true", "yes", "on"}

# IP2Region 数据文件路径
IP2REGION_DB_PATH = os.getenv(
    "IP2REGION_DB_PATH",
    os.path.join(os.path.dirname(__file__), "ip2region", "ip2region_v4.xdb"),
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    echo=DB_ECHO,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

_searcher = None


# 用户主表：记录唯一用户名及最近一次 IP/归属地信息。
class ChatUser(Base):
    __tablename__ = "chat_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    # 按用户+会话+时间建立索引，优化会话历史查询与排序。
    __table_args__ = (
        Index("idx_user_session_time", "user_id", "session_id", "create_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_users.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user: Mapped[ChatUser] = relationship(back_populates="sessions")


def ensure_schema() -> None:
    # 仅负责建表，不做业务数据变更。
    Base.metadata.create_all(bind=engine)


def json_resp(status: int, data: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status, content=data)


def _build_ip2region_searcher():
    # 启动时加载 ip2region 索引，避免每次请求重复读取 xdb。
    if ip2xdb is None or ip2util is None:
        return None
    if not os.path.exists(IP2REGION_DB_PATH):
        logger.warning("ip2region xdb 文件不存在: %s", IP2REGION_DB_PATH)
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
        logger.warning("初始化 ip2region 失败，将使用 Unknown: %s", exc)
        return None


def _close_searcher() -> None:
    if _searcher is None:
        return
    try:
        _searcher.close()
    except Exception:
        pass


def _parse_ip_candidate(value: str) -> str | None:
    # 规范化候选 IP：去掉引号、端口、IPv6 zone、IPv4-mapped 前缀。
    candidate = (value or "").strip().strip('"').strip("'")
    if not candidate or candidate.lower() == "unknown":
        return None

    if candidate.startswith("[") and "]" in candidate:
        candidate = candidate[1 : candidate.index("]")]

    if candidate.startswith("::ffff:"):
        candidate = candidate[7:]

    if "%" in candidate:
        candidate = candidate.split("%", 1)[0]

    if candidate.count(":") == 1 and "." in candidate:
        host, port = candidate.rsplit(":", 1)
        if port.isdigit():
            candidate = host

    try:
        ip_address(candidate)
        return candidate
    except ValueError:
        return None


def _prefer_public_ip(candidates: list[str]) -> str | None:
    # 优先使用公网地址，若无公网则回退到首个合法 IP。
    parsed: list[str] = []
    for c in candidates:
        ip = _parse_ip_candidate(c)
        if ip:
            parsed.append(ip)

    for ip in parsed:
        if ip_address(ip).is_global:
            return ip

    return parsed[0] if parsed else None


def extract_client_ip(req: Request) -> str:
    # 按反向代理常见头顺序提取真实客户端地址。
    direct_headers = [
        req.headers.get("CF-Connecting-IP", ""),
        req.headers.get("True-Client-IP", ""),
        req.headers.get("X-Real-IP", ""),
        req.headers.get("X-Client-IP", ""),
    ]
    chosen = _prefer_public_ip(direct_headers)
    if chosen:
        return chosen

    xff = req.headers.get("X-Forwarded-For", "").strip()
    if xff:
        chosen = _prefer_public_ip([p.strip() for p in xff.split(",")])
        if chosen:
            return chosen

    forwarded = req.headers.get("Forwarded", "").strip()
    if forwarded:
        forwarded_candidates: list[str] = []
        for seg in forwarded.split(","):
            for item in seg.split(";"):
                kv = item.strip()
                if kv.lower().startswith("for="):
                    forwarded_candidates.append(kv.split("=", 1)[1].strip())
        chosen = _prefer_public_ip(forwarded_candidates)
        if chosen:
            return chosen

    remote_addr = cast(str | None, req.client.host if req.client else None)
    return _parse_ip_candidate((remote_addr or "").strip()) or "0.0.0.0"


def normalize_ip(raw_ip: str) -> str:
    ip = (raw_ip or "0.0.0.0").strip()
    if ip.startswith("::ffff:"):
        ip = ip[7:]
    if "%" in ip:
        ip = ip.split("%", 1)[0]
    return ip


def lookup_region(raw_ip: str) -> tuple[str, str]:
    # 查询失败时统一回落 Unknown，避免影响主业务链路。
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


def ensure_user_id_by_username(db: Session, username_raw: str, client_ip: str) -> int:
    # 用户不存在则创建并记录 IP/归属地；存在则不覆盖历史记录。
    username = (username_raw or "").strip() or "default_user"
    ip, region = lookup_region(client_ip)

    user = db.query(ChatUser).filter(ChatUser.username == username).first()
    if user is None:
        user = ChatUser(username=username, ip=ip, region=region)
        db.add(user)
        db.flush()

    user_id = int(user.id or 0)
    if user_id <= 0:
        raise RuntimeError("用户创建或查询失败")
    return user_id


def _to_str_time(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


async def _safe_json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
        return body if isinstance(body, dict) else {}
    except Exception:
        return {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 应用生命周期：启动建表+初始化检索器，关闭时释放资源。
    ensure_schema()
    global _searcher
    _searcher = _build_ip2region_searcher()
    yield
    _close_searcher()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check() -> JSONResponse:
    return json_resp(200, {"code": 200, "message": "ok", "data": {"service": "chat-python-backend"}})


@app.post("/api/chat/record")
async def save_record(request: Request) -> JSONResponse:
    # 接口契约对齐前端 ChatRecord：user_id/session_id/question/answer。
    body = await _safe_json_body(request)
    username = str(body.get("user_id") or "default_user")
    session_id = str(body.get("session_id") or "").strip()
    question = str(body.get("question") or "").strip()
    answer = str(body.get("answer") or "").strip()

    if not session_id or not question or not answer:
        return json_resp(400, {"code": 400, "message": "缺少必要字段：session_id/question/answer"})

    db = SessionLocal()
    try:
        user_id = ensure_user_id_by_username(db, username, extract_client_ip(request))
        turn = ChatSession(user_id=user_id, session_id=session_id, question=question, answer=answer)
        db.add(turn)
        db.flush()
        insert_id = int(turn.id)
        db.commit()
        return json_resp(200, {"code": 200, "message": "保存成功", "data": {"id": insert_id}})
    except Exception as exc:
        db.rollback()
        return json_resp(500, {"code": 500, "message": "服务器错误", "error": str(exc)})
    finally:
        db.close()


@app.api_route("/api/chat/records/{session_id:path}", methods=["GET", "DELETE"])
async def records(session_id: str, request: Request) -> JSONResponse:
    username = (request.query_params.get("user_id") or "default_user").strip() or "default_user"
    db = SessionLocal()
    try:
        user = db.query(ChatUser.id).filter(ChatUser.username == username).first()
        user_id = cast(int | None, user[0] if user else None)

        if request.method == "GET":
            # 将每一轮问答展开为 user/assistant 两条消息，便于前端直接渲染。
            if not user_id:
                return json_resp(200, {"code": 200, "message": "获取成功", "data": []})

            turns = (
                db.query(ChatSession)
                .filter(ChatSession.session_id == session_id, ChatSession.user_id == user_id)
                .order_by(ChatSession.create_time.asc(), ChatSession.id.asc())
                .all()
            )

            messages: list[dict[str, Any]] = []
            for turn in turns:
                ctime = _to_str_time(turn.create_time)
                messages.append(
                    {
                        "id": f"{turn.id}-u",
                        "role": "user",
                        "content": turn.question,
                        "create_time": ctime,
                    }
                )
                messages.append(
                    {
                        "id": f"{turn.id}-a",
                        "role": "assistant",
                        "content": turn.answer,
                        "create_time": ctime,
                    }
                )

            return json_resp(200, {"code": 200, "message": "获取成功", "data": messages})

        if not user_id:
            return json_resp(200, {"code": 200, "message": "删除成功", "data": {"affectedRows": 0}})

        # 删除指定用户下某会话的全部轮次。
        affected = (
            db.query(ChatSession)
            .filter(ChatSession.session_id == session_id, ChatSession.user_id == user_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return json_resp(200, {"code": 200, "message": "删除成功", "data": {"affectedRows": affected}})
    except Exception as exc:
        db.rollback()
        return json_resp(500, {"code": 500, "message": "服务器错误", "error": str(exc)})
    finally:
        db.close()


@app.get("/api/chat/sessions/{user_id:path}")
def sessions(user_id: str, request: Request) -> JSONResponse:
    db = SessionLocal()
    try:
        uid = ensure_user_id_by_username(db, user_id, extract_client_ip(request))
        # 聚合用户会话列表：首条消息、创建时间、最近更新时间。
        rows = db.execute(
            text(
                """
                SELECT cs.session_id,
                       MAX(cs.create_time) AS last_time,
                       MIN(cs.create_time) AS create_time,
                       (
                         SELECT question
                         FROM chat_sessions
                         WHERE session_id = cs.session_id AND user_id = cs.user_id
                         ORDER BY create_time ASC, id ASC
                         LIMIT 1
                       ) AS first_message
                FROM chat_sessions cs
                WHERE cs.user_id = :uid
                GROUP BY cs.session_id, cs.user_id
                ORDER BY last_time DESC
                """
            ),
            {"uid": uid},
        ).mappings().all()

        data: list[dict[str, Any]] = []
        for row in rows:
            data.append(
                {
                    "session_id": row.get("session_id"),
                    "last_time": _to_str_time(row.get("last_time")),
                    "create_time": _to_str_time(row.get("create_time")),
                    "first_message": row.get("first_message"),
                }
            )

        db.commit()
        return json_resp(200, {"code": 200, "message": "获取成功", "data": data})
    except Exception as exc:
        db.rollback()
        return json_resp(500, {"code": 500, "message": "服务器错误", "error": str(exc)})
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=APP_HOST, port=APP_PORT, reload=False)