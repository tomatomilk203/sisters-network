import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class SistersDatabase:
    def __init__(self, db_path: str = "sisters_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """データベースとテーブルを初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 会話履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # メモテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # スケジュールテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    completed BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ユーザープロフィール・設定テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            print("データベース初期化完了")
    
    # === 会話履歴管理 ===
    def save_conversation(self, session_id: str, role: str, content: str):
        """会話を保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversations (session_id, role, content)
                VALUES (?, ?, ?)
            ''', (session_id, role, content))
            conn.commit()
    
    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """会話履歴を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT role, content, timestamp FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (session_id, limit))
            
            rows = cursor.fetchall()
            return [
                {
                    'role': row[0],
                    'content': row[1],
                    'timestamp': row[2]
                }
                for row in reversed(rows)  # 古い順に返す
            ]
    
    def get_recent_conversations(self, session_id: str, hours: int = 24) -> List[Dict]:
        """最近の会話を取得（時間指定）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT role, content, timestamp FROM conversations
                WHERE session_id = ? 
                AND datetime(timestamp) > datetime('now', '-{} hours')
                ORDER BY timestamp ASC
            '''.format(hours), (session_id,))
            
            rows = cursor.fetchall()
            return [
                {
                    'role': row[0],
                    'content': row[1],
                    'timestamp': row[2]
                }
                for row in rows
            ]
    
    # === メモ管理 ===
    def save_memo(self, title: str, content: str, category: str = 'general') -> int:
        """メモを保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO memos (title, content, category)
                VALUES (?, ?, ?)
            ''', (title, content, category))
            conn.commit()
            return cursor.lastrowid
    
    def get_memos(self, category: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """メモを取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT id, title, content, category, created_at, updated_at
                    FROM memos WHERE category = ?
                    ORDER BY updated_at DESC LIMIT ?
                ''', (category, limit))
            else:
                cursor.execute('''
                    SELECT id, title, content, category, created_at, updated_at
                    FROM memos ORDER BY updated_at DESC LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'category': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                }
                for row in rows
            ]
    
    def update_memo(self, memo_id: int, title: str = None, content: str = None, category: str = None):
        """メモを更新"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if title:
                updates.append("title = ?")
                params.append(title)
            if content:
                updates.append("content = ?")
                params.append(content)
            if category:
                updates.append("category = ?")
                params.append(category)
            
            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(memo_id)
                
                query = f"UPDATE memos SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()
    
    def delete_memo(self, memo_id: int):
        """メモを削除"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memos WHERE id = ?", (memo_id,))
            conn.commit()
    
    # === スケジュール管理 ===
    def save_schedule(self, date: str, title: str, time: str = None, description: str = None) -> int:
        """スケジュールを保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO schedules (date, time, title, description)
                VALUES (?, ?, ?, ?)
            ''', (date, time, title, description))
            conn.commit()
            return cursor.lastrowid
    
    def get_schedules(self, date: str = None, month: str = None) -> List[Dict]:
        """スケジュールを取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if date:
                cursor.execute('''
                    SELECT id, date, time, title, description, completed, created_at
                    FROM schedules WHERE date = ?
                    ORDER BY time ASC, created_at ASC
                ''', (date,))
            elif month:
                cursor.execute('''
                    SELECT id, date, time, title, description, completed, created_at
                    FROM schedules WHERE date LIKE ?
                    ORDER BY date ASC, time ASC
                ''', (f"{month}%",))
            else:
                cursor.execute('''
                    SELECT id, date, time, title, description, completed, created_at
                    FROM schedules WHERE date >= date('now')
                    ORDER BY date ASC, time ASC
                    LIMIT 50
                ''')
            
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'date': row[1],
                    'time': row[2],
                    'title': row[3],
                    'description': row[4],
                    'completed': bool(row[5]),
                    'created_at': row[6]
                }
                for row in rows
            ]
    
    def update_schedule(self, schedule_id: int, **kwargs):
        """スケジュールを更新"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            for key, value in kwargs.items():
                if key in ['date', 'time', 'title', 'description', 'completed']:
                    updates.append(f"{key} = ?")
                    params.append(value)
            
            if updates:
                params.append(schedule_id)
                query = f"UPDATE schedules SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()
    
    def delete_schedule(self, schedule_id: int):
        """スケジュールを削除"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            conn.commit()
    
    # === ユーザープロフィール管理 ===
    def save_user_profile(self, key: str, value: str):
        """ユーザー情報を保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_profiles (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            conn.commit()
    
    def get_user_profile(self, key: str) -> Optional[str]:
        """ユーザー情報を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_profiles WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def get_all_user_profiles(self) -> Dict[str, str]:
        """全ユーザー情報を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM user_profiles")
            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows}
    
    # === メンテナンス ===
    def cleanup_old_conversations(self, days: int = 30):
        """古い会話履歴を削除"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM conversations 
                WHERE datetime(timestamp) < datetime('now', '-{} days')
            '''.format(days))
            conn.commit()
            print(f"{days}日以前の会話履歴を削除しました")
    
    def get_database_stats(self) -> Dict:
        """データベースの統計情報"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # 各テーブルの件数
            tables = ['conversations', 'memos', 'schedules', 'user_profiles']
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()[0]
            
            return stats

# 使用例とテスト用のコード
if __name__ == "__main__":
    # データベースのテスト
    db = SistersDatabase()
    
    # テストデータ
    session_id = "test_session"
    
    # 会話履歴のテスト
    db.save_conversation(session_id, "user", "こんにちは")
    db.save_conversation(session_id, "assistant", "こんにちは！と、ミサカは挨拶を返します。")
    
    # メモのテスト
    memo_id = db.save_memo("テストメモ", "これはテスト用のメモです", "test")
    
    # スケジュールのテスト
    schedule_id = db.save_schedule("2025-08-29", "勉強会", "14:00", "プログラミング勉強会")
    
    # 統計情報の表示
    stats = db.get_database_stats()
    print("データベース統計:", stats)