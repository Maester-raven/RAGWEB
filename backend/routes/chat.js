const express = require('express');
const router = express.Router();
const pool = require('../db');

// 1. 保存单条对话记录
router.post('/record', async (req, res) => {
  try {
    const { user_id = 'default_user', session_id, role, content } = req.body;
    const [result] = await pool.execute(
      'INSERT INTO chat_records (user_id, session_id, role, content) VALUES (?, ?, ?, ?)',
      [user_id, session_id, role, content]
    );
    res.json({
      code: 200,
      message: '保存成功',
      data: { id: result.insertId }
    });
  } catch (err) {
    res.status(500).json({ code: 500, message: '保存失败', error: err.message });
  }
});

// 2. 获取指定会话的历史记录
router.get('/records/:session_id', async (req, res) => {
  try {
    const { session_id } = req.params;
    const { user_id = 'default_user' } = req.query;
    const [rows] = await pool.execute(
      'SELECT * FROM chat_records WHERE session_id = ? AND user_id = ? ORDER BY create_time ASC',
      [session_id, user_id]
    );
    res.json({ code: 200, message: '获取成功', data: rows });
  } catch (err) {
    res.status(500).json({ code: 500, message: '获取失败', error: err.message });
  }
});

// 3. 删除指定会话的所有记录
router.delete('/records/:session_id', async (req, res) => {
  try {
    const { session_id } = req.params;
    const { user_id = 'default_user' } = req.query;
    const [result] = await pool.execute(
      'DELETE FROM chat_records WHERE session_id = ? AND user_id = ?',
      [session_id, user_id]
    );
    res.json({
      code: 200,
      message: '删除成功',
      data: { affectedRows: result.affectedRows }
    });
  } catch (err) {
    res.status(500).json({ code: 500, message: '删除失败', error: err.message });
  }
});

module.exports = router;