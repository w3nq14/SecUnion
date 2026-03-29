import sqlite3
import json
import os
from datetime import datetime


class Storage:
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'data', 'blogs.db')
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        self._migrate_from_json()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS blogs (
                    url TEXT PRIMARY KEY,
                    name TEXT,
                    friends TEXT,
                    is_accessible INTEGER DEFAULT 1,
                    friend_page_url TEXT,
                    last_crawled TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    source TEXT,
                    target TEXT,
                    PRIMARY KEY (source, target)
                )
            """)
            conn.commit()

    def _migrate_from_json(self):
        """自动从旧 JSON 文件迁移数据"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base_dir, 'data', 'blogs.json')

        if not os.path.exists(json_path):
            return

        # 检查 SQLite 是否已有数据
        with self._get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM blogs").fetchone()[0]
            if count > 0:
                return  # 已有数据，跳过迁移

        print(f"[Storage] 检测到旧 JSON 数据库，开始迁移...")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        blogs = data.get('blogs', {})
        edges = data.get('edges', [])

        with self._get_conn() as conn:
            for url, blog in blogs.items():
                conn.execute("""
                    INSERT OR IGNORE INTO blogs (url, name, friends, is_accessible, friend_page_url, last_crawled)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    url,
                    blog.get('name', ''),
                    json.dumps(blog.get('friends', []), ensure_ascii=False),
                    1 if blog.get('is_accessible', True) else 0,
                    blog.get('friend_page_url'),
                    blog.get('last_crawled', datetime.now().isoformat())
                ))

            for edge in edges:
                conn.execute("""
                    INSERT OR IGNORE INTO edges (source, target) VALUES (?, ?)
                """, (edge['source'], edge['target']))

            conn.commit()

        # 重命名 JSON 文件为备份
        bak_path = json_path + '.bak'
        os.rename(json_path, bak_path)
        print(f"[Storage] 迁移完成！共迁移 {len(blogs)} 个博客，{len(edges)} 条边。JSON 备份至 {bak_path}")

    def save_blog(self, url, name, friends, is_accessible=True, friend_page_url=None):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO blogs (url, name, friends, is_accessible, friend_page_url, last_crawled)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                url,
                name,
                json.dumps(friends, ensure_ascii=False),
                1 if is_accessible else 0,
                friend_page_url,
                datetime.now().isoformat()
            ))

            for friend in friends:
                conn.execute("""
                    INSERT OR IGNORE INTO edges (source, target) VALUES (?, ?)
                """, (url, friend))

            conn.commit()

    def get_blog(self, url):
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM blogs WHERE url = ?", (url,)).fetchone()
            if row:
                return self._row_to_dict(row)
            return None

    def get_all_blogs(self):
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM blogs").fetchall()
            return {row['url']: self._row_to_dict(row) for row in rows}

    def get_edges(self):
        with self._get_conn() as conn:
            rows = conn.execute("SELECT source, target FROM edges").fetchall()
            return [{"source": row['source'], "target": row['target']} for row in rows]

    def update_accessibility(self, url, is_accessible):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE blogs SET is_accessible = ? WHERE url = ?",
                (1 if is_accessible else 0, url)
            )
            conn.commit()

    def get_all_friend_pages(self):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT url, friend_page_url FROM blogs WHERE friend_page_url IS NOT NULL AND friend_page_url != ''"
            ).fetchall()
            return [{"url": row['url'], "friend_page_url": row['friend_page_url']} for row in rows]

    def get_edges_for_nodes(self, urls):
        """查询一批节点相关的所有边（出链+入链）"""
        if not urls:
            return []
        placeholders = ','.join('?' * len(urls))
        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT source, target FROM edges WHERE source IN ({placeholders}) OR target IN ({placeholders})",
                list(urls) + list(urls)
            ).fetchall()
            return [{"source": row['source'], "target": row['target']} for row in rows]

    def delete_blog(self, url):
        """删除博客及其相关边（用于黑名单功能）"""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM blogs WHERE url = ?", (url,))
            conn.execute("DELETE FROM edges WHERE source = ? OR target = ?", (url, url))
            conn.commit()

    def _row_to_dict(self, row):
        return {
            "name": row['name'],
            "url": row['url'],
            "friends": json.loads(row['friends']) if row['friends'] else [],
            "is_accessible": bool(row['is_accessible']),
            "friend_page_url": row['friend_page_url'],
            "last_crawled": row['last_crawled']
        }
