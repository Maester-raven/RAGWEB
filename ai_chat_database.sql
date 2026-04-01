-- AI 对话数据库设计

-- 用户表
CREATE TABLE chat_users (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    username String(64) UNIQUE NOT NULL,
    ip String(45) NULL,
    region String(255) NULL,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 对话会话表
CREATE TABLE chat_sessions (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id BIGINT NOT NULL,
    session_id String(64) NOT NULL,
    question Text NOT NULL,
    answer Text NOT NULL,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES chat_users(id) ON UPDATE CASCADE ON DELETE CASCADE
);

-- 添加索引
CREATE INDEX idx_user_session_time ON chat_sessions (user_id, session_id, create_time);