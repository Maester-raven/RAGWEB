const express = require('express');
const cors = require('cors');
require('dotenv').config();
const pool = require('./db');

const app = express();
const PORT = process.env.PORT || 3000;

// 中间件
app.use(cors());
app.use(express.json());

// 聊天路由
const chatRoutes = require('./routes/chat');
app.use('/api/chat', chatRoutes);

// 健康检查
app.get('/', (req, res) => {
  res.send('✅ RAGWEB Backend is running');
});

// 启动服务
app.listen(PORT, () => {
  console.log(`🚀 后端服务运行在 http://localhost:${PORT}`);
  // 测试数据库连接
  pool.getConnection()
    .then(conn => {
      console.log('✅ 数据库连接成功');
      conn.release();
    })
    .catch(err => {
      console.error('❌ 数据库连接失败:', err.message);
    });
});