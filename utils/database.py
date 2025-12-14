"""
Database module for Facebook Discord Bot
Handles all MongoDB operations
"""

from pymongo import MongoClient
from datetime import datetime
from cryptography.fernet import Fernet
import config


class Database:
    """Database handler for Facebook"""
    
    def __init__(self):
        """Initialize MongoDB connection"""
        try:
            self.client = MongoClient(config.MONGODB_URI)
            self.db = self.client[config.DATABASE_NAME]
            
            # Facebook collections
            self.facebook_accounts = self.db['facebook_accounts']
            self.facebook_posts = self.db['facebook_posts']
            self.facebook_analytics = self.db['facebook_analytics']
            
            # Initialize encryption
            self.cipher = Fernet(config.ENCRYPTION_KEY.encode())
            
            print('✅ Database connected')
        except Exception as e:
            print(f'❌ Database connection failed: {e}')
            raise
    
    def encrypt(self, text):
        """Encrypt access token"""
        return self.cipher.encrypt(text.encode()).decode()
    
    def decrypt(self, encrypted):
        """Decrypt access token"""
        return self.cipher.decrypt(encrypted.encode()).decode()
    
    # Facebook Account Methods
    def save_facebook_account(self, server_id, account_data):
        """Save Facebook page for a Discord server"""
        account_data['access_token'] = self.encrypt(account_data['access_token'])
        account_data['server_id'] = str(server_id)
        account_data['connected_at'] = datetime.utcnow()
        
        self.facebook_accounts.update_one(
            {'server_id': str(server_id)},
            {'$set': account_data},
            upsert=True
        )
        print(f'✅ Saved Facebook account for server {server_id}')
    
    def get_facebook_account(self, server_id):
        """Get Facebook page for a server"""
        account = self.facebook_accounts.find_one({'server_id': str(server_id)})
        if account and 'access_token' in account:
            account['access_token'] = self.decrypt(account['access_token'])
        return account
    
    def delete_facebook_account(self, server_id):
        """Delete Facebook account"""
        result = self.facebook_accounts.delete_one({'server_id': str(server_id)})
        print(f'✅ Deleted Facebook account for server {server_id}')
        return result.deleted_count > 0
    
    # Post Methods
    def save_facebook_post(self, post_data):
        """Save a Facebook post (scheduled or published)"""
        post_data['created_at'] = datetime.utcnow()
        result = self.facebook_posts.insert_one(post_data)
        print(f'✅ Saved post with ID {result.inserted_id}')
        return result.inserted_id
    
    def get_facebook_scheduled_posts(self):
        """Get Facebook posts that need to be published"""
        posts = list(self.facebook_posts.find({
            'status': 'scheduled',
            'scheduled_at': {'$lte': datetime.utcnow()}
        }))
        return posts
    
    def update_facebook_post_status(self, post_id, status, fb_post_id=None):
        """Update post status after publishing"""
        update = {
            'status': status,
            'published_at': datetime.utcnow()
        }
        if fb_post_id:
            update['fb_post_id'] = fb_post_id
        
        self.facebook_posts.update_one(
            {'_id': post_id},
            {'$set': update}
        )
        print(f'✅ Updated post {post_id} status to {status}')
    
    def get_posts_by_server(self, server_id, limit=10):
        """Get posts for a server"""
        return list(self.facebook_posts.find(
            {'server_id': str(server_id)}
        ).sort('created_at', -1).limit(limit))
    
    # Analytics Methods
    def save_facebook_analytics(self, analytics_data):
        """Save Facebook post analytics"""
        analytics_data['fetched_at'] = datetime.utcnow()
        result = self.facebook_analytics.insert_one(analytics_data)
        return result.inserted_id
    
    def get_analytics(self, post_id):
        """Get latest analytics for a post"""
        return self.facebook_analytics.find_one(
            {'post_id': post_id},
            sort=[('fetched_at', -1)]
        )


# Global database instance
db = Database()

import sqlite3
import os

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
    """Get the Instagram token for a Discord user"""
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
        create_tables(conn)
    conn = get_db_connection(db_path)
    conn.close()
    print("data base initialized")
    
    
    
    
