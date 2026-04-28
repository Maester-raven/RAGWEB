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
    import IP2Location  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    IP2Location = None


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

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:123456@localhost:5432/ai_chat")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "9000"))

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))
DB_ECHO = os.getenv("DB_ECHO", "false").lower() in {"1", "true", "yes", "on"}

IP2LOCATION_DB_PATH = os.getenv(
    "IP2LOCATION_DB_PATH",
    os.path.join(os.path.dirname(__file__), "ip2region", "data", "IP2LOCATION-LITE-DB3.BIN"),
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

_location_db = None


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
    Base.metadata.create_all(bind=engine)


def json_resp(status: int, data: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status, content=data)


def _build_ip2location_db():
    if IP2Location is None:
        logger.warning("IP2Location package not installed, region lookup disabled")
        return None

    if not os.path.exists(IP2LOCATION_DB_PATH):
        logger.warning("IP2Location BIN file not found: %s", IP2LOCATION_DB_PATH)
        return None

    try:
        return IP2Location.IP2Location(IP2LOCATION_DB_PATH)
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to initialize IP2Location, fallback to Unknown: %s", exc)
        return None


def _close_location_db() -> None:
    if _location_db is None:
        return

    try:
        close_fn = getattr(_location_db, "close", None)
        if callable(close_fn):
            close_fn()
    except Exception:
        pass


def _parse_ip_candidate(value: str) -> str | None:
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


def _clean_location_value(value: Any) -> str:
    text_value = str(value or "").strip()
    if not text_value or text_value in {"-", "NOT_SUPPORTED", "Not_Supported"}:
        return ""
    return text_value


def lookup_region(raw_ip: str) -> tuple[str, str]:
    ip = normalize_ip(raw_ip)
    try:
        ip_address(ip)
    except ValueError:
        return ip, "Unknown"

    if _location_db is None:
        return ip, "Unknown"

    try:
        record = _location_db.get_all(ip)
        country = _clean_location_value(getattr(record, "country_name", ""))
        region = _clean_location_value(getattr(record, "region_name", ""))
        city = _clean_location_value(getattr(record, "city_name", ""))
        parts = [country, region, city]
        region = " | ".join([part for part in parts if part])
        return ip, (region or "Unknown")
    except Exception:
        return ip, "Unknown"


def ensure_user_id_by_username(db: Session, username_raw: str, client_ip: str) -> int:
    username = (username_raw or "").strip() or "default_user"
    ip, region = lookup_region(client_ip)

    user = db.query(ChatUser).filter(ChatUser.username == username).first()
    if user is None:
        user = ChatUser(username=username, ip=ip, region=region)
        db.add(user)
        db.flush()

    user_id = int(user.id or 0)
    if user_id <= 0:
        raise RuntimeError("failed to create or query user")
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
    ensure_schema()
    global _location_db
    _location_db = _build_ip2location_db()
    yield
    _close_location_db()


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
    body = await _safe_json_body(request)
    username = str(body.get("user_id") or "default_user")
    session_id = str(body.get("session_id") or "").strip()
    question = str(body.get("question") or "").strip()
    answer = str(body.get("answer") or "").strip()

    if not session_id or not question or not answer:
        return json_resp(400, {"code": 400, "message": "missing required fields: session_id/question/answer"})

    db = SessionLocal()
    try:
        user_id = ensure_user_id_by_username(db, username, extract_client_ip(request))
        turn = ChatSession(user_id=user_id, session_id=session_id, question=question, answer=answer)
        db.add(turn)
        db.flush()
        insert_id = int(turn.id)
        db.commit()
        return json_resp(200, {"code": 200, "message": "saved", "data": {"id": insert_id}})
    except Exception as exc:
        db.rollback()
        return json_resp(500, {"code": 500, "message": "server error", "error": str(exc)})
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
            if not user_id:
                return json_resp(200, {"code": 200, "message": "ok", "data": []})

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

            return json_resp(200, {"code": 200, "message": "ok", "data": messages})

        if not user_id:
            return json_resp(200, {"code": 200, "message": "deleted", "data": {"affectedRows": 0}})

        affected = (
            db.query(ChatSession)
            .filter(ChatSession.session_id == session_id, ChatSession.user_id == user_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return json_resp(200, {"code": 200, "message": "deleted", "data": {"affectedRows": affected}})
    except Exception as exc:
        db.rollback()
        return json_resp(500, {"code": 500, "message": "server error", "error": str(exc)})
    finally:
        db.close()


@app.get("/api/chat/sessions/{user_id:path}")
def sessions(user_id: str, request: Request) -> JSONResponse:
    db = SessionLocal()
    try:
        uid = ensure_user_id_by_username(db, user_id, extract_client_ip(request))
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
        return json_resp(200, {"code": 200, "message": "ok", "data": data})
    except Exception as exc:
        db.rollback()
        return json_resp(500, {"code": 500, "message": "server error", "error": str(exc)})
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main_location:app", host=APP_HOST, port=APP_PORT, reload=False)
