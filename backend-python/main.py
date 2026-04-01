from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ipaddress import ip_address
import os
from datetime import datetime

# --- 1. 数据库配置 (ORM 优化部分 - 对应原 A/B/D 功能) ---
# 这里简化了原 app.py 中手动读取 .env 和复杂的连接池管理
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/ai_chat")
if not DATABASE_URL:
    raise RuntimeError("请在 .env 文件中配置 DATABASE_URL，或者设置环境变量")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_message = Column(Text, nullable=False)
    ip_address = Column(String(45), nullable=True)  # 存储IP地址
    location = Column(String(255), nullable=True)   # 存储IP地理位置``
    timestamp = Column(DateTime, default=datetime.utcnow)

# 创建表 (替代原 ensure_schema 的自动建表逻辑)
Base.metadata.create_all(bind=engine)

# --- 2. IP2Region 初始化 (保持原样，但适配 FastAPI 结构) ---
try:
    import ip2region.searcher as ip2xdb
    import ip2region.util as ip2util
except Exception as e:
    ip2xdb = None
    ip2util = None

IP2REGION_DB_PATH = os.getenv(
    "IP2REGION_DB_PATH",
    os.path.join(os.path.dirname(__file__), "ip2region", "ip2region_v4.xdb"),
)

_searcher = None

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


def _parse_ip_candidate(value: str) -> str | None:
    candidate = (value or "").strip().strip('"').strip("'")
    if not candidate or candidate.lower() == "unknown":
        return None
    
    if candidate.startswith("[") and "]" in candidate:
        candidate = candidate[1: candidate.index("]")]

    if candidate.startswith("::ffff:"):
        candidate = candidate[7:]

    if "%" in candidate:
        candidate = candidate.split("%", 1)[0]

    # IPv4 with port: 1.2.3.4:5678
    if candidate.count(":") == 1 and "." in candidate:
        host, port = candidate.rsplit(":", 1)
        if port.isdigit():
            candidate = host
        
    try:
        ip_address(candidate)
        return candidate
    except Exception:
        return None


def _prefer_public_ip(candidates: list[str]) -> str | None:
    parsed: list[str] = []
    for c in candidates:
        ip = _parse_ip_candidate(c)
        if ip:
            parsed.append(ip)
    
    for ip in parsed:
        ip_obj = ip_address(ip)
        if ip_obj.is_global: 
            return ip
    
    return parsed[0] if parsed else None

def extract_client_ip(request) -> str:
    direct_headers = [
        request.headers.get("CF-Connecting-IP", ""),
        request.headers.get("True-Client-IP", ""),
        request.headers.get("X-Real-IP", ""),
        request.headers.get("X-Client-IP", ""),
    ]
    chosen = _prefer_public_ip(direct_headers)
    if chosen:
        return chosen

    xff = request.headers.get("X-Forwarded-For", "").strip()
    if xff:
        chosen = _prefer_public_ip([p.strip() for p in xff.split(",")])
        if chosen:
            return chosen

    forwarded = request.headers.get("Forwarded", "").strip()
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

    return _parse_ip_candidate(request.client.host) or "0.0.0.0"


def normalize_ip(raw_ip: str) -> str:
    if not raw_ip:
        return "0.0.0.0"
    ip = raw_ip.strip()
    if ip.startswith("::ffff:"):
        ip = ip[7:]
    if "%" in ip:
        ip = ip.split("%", 1)[0]
    return ip

# --- 4. 聊天接口 (整合 ORM 与 原生 IP 逻辑) ---
app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat/")
async def chat(request: Request, user_message: str):
    db = SessionLocal()
    try:
        # 1. 使用保留的原生复杂逻辑获取 IP
        raw_ip = extract_client_ip(request)
        
        # 2. 使用 IP2Region 查询地理位置
        location = "Unknown"
        if _searcher and raw_ip != "0.0.0.0":
            try:
                region_data = _searcher.search(raw_ip)
                # 直接判断 region_data 是否存在，如果是字符串就直接赋值
                if region_data: # 如果查询成功，region_data 会是字符串
                    location = region_data # 直接把字符串给 location
                else: # 如果查询失败，region_data 会是 None 或空
                    location = "Unknown"
            except:
                location = "Unknown"

        # 3. 使用 ORM 保存数据 (替代了原生的 SQL 拼接)
        chat_record = ChatHistory(
            user_message=user_message,
            ip_address=raw_ip,
            location=location
        )
        db.add(chat_record)
        db.commit()
        db.refresh(chat_record)

        return {
            "response": f"收到: {user_message}",
            "location": location,
            "raw_ip": raw_ip,
            "id": chat_record.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    global _searcher
    _searcher = _build_ip2region_searcher()
    if _searcher:
        print("IP查询功能已启动")
    else:
        print("警告：IP查询功能启动失败")