"""
Database module for Facebook Discord Bot
Handles all database operations (SQLite)
"""

import sqlite3
import json
from datetime import datetime
from cryptography.fernet import Fernet
import config
import os

DB_PATH = 'database.db'

class Database:
    """Database handler for Facebook (SQLite Adapter)"""
    
    def __init__(self):
        """Initialize SQLite tables"""
        try:
            self.cipher = Fernet(config.ENCRYPTION_KEY.encode())
            self._init_tables()
            print('Database connected (SQLite)')
        except Exception as e:
            print(f'Database connection failed: {e}')
            raise
            
    def _get_conn(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        conn = self._get_conn()
        cur = conn.cursor()
        
        # Facebook Accounts
        cur.execute('''
        CREATE TABLE IF NOT EXISTS facebook_accounts (
            server_id TEXT PRIMARY KEY,
            page_id TEXT,
            page_name TEXT,
            access_token TEXT,
            connected_at TIMESTAMP
        )''')
        
        # Facebook Posts
        cur.execute('''
        CREATE TABLE IF NOT EXISTS facebook_posts (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id TEXT,
            page_id TEXT,
            fb_post_id TEXT,
            message TEXT,
            link TEXT,
            image_url TEXT,
            status TEXT,
            platform TEXT,
            scheduled_at TIMESTAMP,
            published_at TIMESTAMP,
            created_at TIMESTAMP
        )''')
        
        # Facebook Analytics
        cur.execute('''
        CREATE TABLE IF NOT EXISTS facebook_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT,
            server_id TEXT,
            post_impressions INTEGER,
            post_engaged_users INTEGER,
            post_clicks INTEGER,
            fetched_at TIMESTAMP,
            raw_data TEXT
        )''')
        
        conn.commit()
        conn.close()
    
    def encrypt(self, text):
        return self.cipher.encrypt(text.encode()).decode()
    
    def decrypt(self, encrypted):
        return self.cipher.decrypt(encrypted.encode()).decode()
    
    # Facebook Account Methods
    def save_facebook_account(self, server_id, account_data):
        conn = self._get_conn()
        try:
            encrypted_token = self.encrypt(account_data['access_token'])
            conn.execute('''
                INSERT OR REPLACE INTO facebook_accounts 
                (server_id, page_id, page_name, access_token, connected_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                str(server_id),
                account_data.get('page_id'),
                account_data.get('page_name'),
                encrypted_token,
                datetime.utcnow()
            ))
            conn.commit()
            print(f'Saved Facebook account for server {server_id}')
        finally:
            conn.close()
    
    def get_facebook_account(self, server_id):
        conn = self._get_conn()
        try:
            row = conn.execute('SELECT * FROM facebook_accounts WHERE server_id = ?', (str(server_id),)).fetchone()
            if row:
                data = dict(row)
                if data['access_token']:
                    data['access_token'] = self.decrypt(data['access_token'])
                return data
            return None
        finally:
            conn.close()
    
    def delete_facebook_account(self, server_id):
        conn = self._get_conn()
        try:
            cur = conn.execute('DELETE FROM facebook_accounts WHERE server_id = ?', (str(server_id),))
            conn.commit()
            print(f'Deleted Facebook account for server {server_id}')
            return cur.rowcount > 0
        finally:
            conn.close()
    
    # Post Methods
    def save_facebook_post(self, post_data):
        conn = self._get_conn()
        try:
            cur = conn.execute('''
                INSERT INTO facebook_posts 
                (server_id, page_id, fb_post_id, message, link, image_url, status, platform, scheduled_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_data.get('server_id'),
                post_data.get('page_id'),
                post_data.get('fb_post_id'),
                post_data.get('message'),
                post_data.get('link'),
                post_data.get('image_url'),
                post_data.get('status'),
                post_data.get('platform'),
                post_data.get('scheduled_at'),
                datetime.utcnow()
            ))
            conn.commit()
            print(f'Saved post with ID {cur.lastrowid}')
            return cur.lastrowid
        finally:
            conn.close()
            
    def get_facebook_scheduled_posts(self):
        conn = self._get_conn()
        try:
            rows = conn.execute('''
                SELECT * FROM facebook_posts 
                WHERE status = 'scheduled' AND scheduled_at <= ?
            ''', (datetime.utcnow(),)).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
            
    def update_facebook_post_status(self, post_id, status, fb_post_id=None):
        conn = self._get_conn()
        try:
            if fb_post_id:
                conn.execute('UPDATE facebook_posts SET status = ?, published_at = ?, fb_post_id = ? WHERE _id = ?',
                           (status, datetime.utcnow(), fb_post_id, post_id))
            else:
                conn.execute('UPDATE facebook_posts SET status = ?, published_at = ? WHERE _id = ?',
                           (status, datetime.utcnow(), post_id))
            conn.commit()
            print(f'Updated post {post_id} status to {status}')
        finally:
            conn.close()

    def save_facebook_analytics(self, analytics_data):
        conn = self._get_conn()
        try:
            # simple json dump for raw extra fields if needed, but we mapped the main ones
            cur = conn.execute('''
                INSERT INTO facebook_analytics 
                (post_id, server_id, post_impressions, post_engaged_users, post_clicks, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                analytics_data.get('post_id'),
                analytics_data.get('server_id'),
                analytics_data.get('post_impressions'),
                analytics_data.get('post_engaged_users'),
                analytics_data.get('post_clicks'),
                datetime.utcnow()
            ))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

# Global database instance
db = Database()

# --- INSTAGRAM / FUNCTIONAL PART (Maintained for compatibility) ---
def create_tables(conn):
    with conn:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            instagram_id TEXT,
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT NOT NULL UNIQUE,
            instagram_token TEXT NOT NULL,
            username TEXT NOT NULL
        );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                post_id TEXT NOT NULL,
                caption TEXT,
                media_url TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        ''')

def get_db_connection(db_path='database.db'): 
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path='database.db'):
    conn = get_db_connection(db_path)
    create_tables(conn)
    conn.close()

def close_db_connection(conn):
    conn.close()

def insert_user(conn, discord_id, username, instagram_token):
    with conn:
        conn.execute('''
            INSERT OR REPLACE INTO users (discord_id, username, instagram_token)
            VALUES (?, ?, ?);
        ''', (discord_id, username, instagram_token))

def get_user_token(conn, discord_id):
    cursor = conn.execute('''
        SELECT instagram_token, username FROM users
        WHERE discord_id = ?;
    ''', (str(discord_id),))
    result = cursor.fetchone()
    return result if result else None

def insert_post(conn, user_id, post_id, caption, media_url):
    with conn:
        conn.execute('''
            INSERT INTO posts (user_id, post_id, caption, media_url)
            VALUES (?, ?, ?, ?);
        ''', (user_id, post_id, caption, media_url))

def initialize_database(db_path='database.db'):
    if not os.path.exists(db_path):
        init_db(db_path)
    else:
        # ensure tables exist even if file exists
        init_db(db_path)
    print("Database initialized")
