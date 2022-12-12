import sqlite3
from .constants import DB_FILE


class DBHelper:
    conn = None
    cursor = None

    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.execute('CREATE TABLE IF NOT EXISTS users \
            (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
            telegram_user_id TEXT, first_name TEXT, username TEXT)')
        self.conn.execute('CREATE TABLE IF NOT EXISTS tracking\
             (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
             user_id INT, chat_id INT, url TEXT, type TEXT)')
        self.conn.commit()
        self.cursor = self.conn.cursor()

    def insert_user(self, telegram_user_id, first_name, username):
        self.cursor.execute(
            "INSERT INTO users (telegram_user_id,\
             first_name, username) VALUES (?, ?, ?)",
            (telegram_user_id, first_name, username))
        last_id = self.cursor.lastrowid
        self.conn.commit()
        return last_id

    def fetch_user(self, telegram_user_id):
        self.cursor.execute("SELECT * FROM users WHERE telegram_user_id = ?",
                            (telegram_user_id,))
        return self.cursor.fetchone()

    def insert_tracking(self, telegram_user_id, chat_id, url, type_of_compare):
        user = self.fetch_user(telegram_user_id)
        self.cursor.execute("INSERT INTO tracking (user_id, chat_id, url,\
                             type) VALUES (?, ?, ?, ?)",
                            (user[0], chat_id, url, type_of_compare))
        last_id = self.cursor.lastrowid
        self.conn.commit()
        return last_id

    def fetch_tracking(self, id):
        self.cursor.execute("SELECT * FROM tracking WHERE id = ?", (id,))
        return self.cursor.fetchone()

    def delete_tracking(self, id):
        self.cursor.execute("DELETE FROM tracking WHERE id = ?", (id,))
        self.conn.commit()

    def list_tracking(self, telegram_user_id):
        user = self.fetch_user(telegram_user_id)
        if user is None:
            return "You are not tracking anything"

        self.cursor.execute("SELECT * FROM tracking WHERE user_id = ?",
                            (user[0],))
        urls = self.cursor.fetchall()
        if len(urls) == 0:
            return "You are not tracking anything"
        return urls

    def list_all_tracking(self):
        self.cursor.execute("SELECT * FROM tracking")
        return self.cursor.fetchall()

    def delete_tracking(self, id):
        self.cursor.execute("DELETE FROM tracking WHERE id = ?", (id,))
        self.conn.commit()
