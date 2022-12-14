import sqlite3
import os
import mysql.connector
from datetime import datetime

from .constants import DB_FILE


Queries = {
    'sqlite': {
        'create_users': 'CREATE TABLE IF NOT EXISTS users \
                (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                telegram_user_id TEXT, first_name TEXT, username TEXT)',
        'create_tracking': 'CREATE TABLE IF NOT EXISTS tracking\
                (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                user_id INT, chat_id INT, url TEXT, type TEXT,\
                old_image TEXT, new_image TEXT, last_run TEXT)',
        'create_feedback': 'CREATE TABLE IF NOT EXISTS feedback\
                (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                user_id INT, feedback TEXT, date TEXT)',
        'insert_feedback': 'INSERT INTO feedback (user_id, feedback, date)'
        ' VALUES (?, ?, ?)',
        'get_all_feedback': 'SELECT * FROM feedback',
        'insert_user': 'INSERT INTO users (telegram_user_id, '
        'first_name, username) VALUES (?, ?, ?)',
        'insert_tracking': 'INSERT INTO tracking (user_id, chat_id,'
        'url, type) VALUES (?, ?, ?, ?)',
        'get_user': 'SELECT * FROM users WHERE telegram_user_id = ?',
        'get_all_tracking': 'SELECT * FROM tracking',
        'get_tracking': 'SELECT * FROM tracking WHERE user_id = ?',
        'get_tracking_by_id': 'SELECT * FROM tracking WHERE id = ?',
        'get_tracking_by_url': 'SELECT * FROM tracking WHERE url = ?',
        'update_tracking': 'UPDATE tracking SET old_image = ?, '
        'new_image = ?, last_run = ? WHERE id = ?',
        'update_tracking_old_image': 'UPDATE tracking SET old_image = ?'
        ' WHERE id = ?',
        'update_tracking_new_image': 'UPDATE tracking SET new_image = ?'
        ' WHERE id = ?',
        'update_tracking_last_run': 'UPDATE tracking SET last_run = ?'
        ' WHERE id = ?',
        'delete_tracking': 'DELETE FROM tracking WHERE id = ?'
    },
    'mysql': {
        'create_users': 'CREATE TABLE IF NOT EXISTS users \
                (id INT NOT NULL AUTO_INCREMENT, \
                telegram_user_id TEXT, first_name TEXT, username TEXT,\
                PRIMARY KEY (id))',
        'create_tracking': 'CREATE TABLE IF NOT EXISTS tracking\
                (id INT NOT NULL AUTO_INCREMENT, \
                user_id INT, chat_id INT, url TEXT, type TEXT,\
                old_image TEXT, new_image TEXT, last_run TEXT,\
                PRIMARY KEY (id))',
        'create_feedback': 'CREATE TABLE IF NOT EXISTS feedback\
                (id INT NOT NULL AUTO_INCREMENT, \
                user_id INT, feedback TEXT, date TEXT,\
                PRIMARY KEY (id))',
        'insert_feedback': 'INSERT INTO feedback (user_id, feedback, date)'
        ' VALUES (%s, %s, %s)',
        'get_all_feedback': 'SELECT * FROM feedback',
        'insert_user': 'INSERT INTO users (telegram_user_id, first_name, '
        'username) VALUES (%s, %s, %s)',
        'insert_tracking': 'INSERT INTO tracking (user_id, chat_id, url, type)'
        ' VALUES (%s, %s, %s, %s)',
        'get_user': 'SELECT * FROM users WHERE telegram_user_id = %s',
        'get_all_tracking': 'SELECT * FROM tracking',
        'get_tracking': 'SELECT * FROM tracking WHERE user_id = %s',
        'get_tracking_by_id': 'SELECT * FROM tracking WHERE id = %s',
        'get_tracking_by_url': 'SELECT * FROM tracking WHERE url = %s',
        'update_tracking': 'UPDATE tracking SET old_image = %s, '
        'new_image = %s, last_run = %s WHERE id = %s',
        'update_tracking_old_image': 'UPDATE tracking SET '
        'old_image = %s WHERE id = %s',
        'update_tracking_new_image': 'UPDATE tracking SET '
        'new_image = %s WHERE id = %s',
        'update_tracking_last_run': 'UPDATE tracking SET '
        'last_run = %s WHERE id = %s',
        'delete_tracking': 'DELETE FROM tracking WHERE id = %s'
    }
}


class DBHelper:
    conn = None
    cursor = None

    def _create_tables(self):
        self._execute_(Queries[self.db_type]['create_users'])
        self._execute_(Queries[self.db_type]['create_tracking'])
        self._execute_(Queries[self.db_type]['create_feedback'])
        self.conn.commit()

    def _init_db(self):
        if self.db_type == 'sqlite':
            self.conn = sqlite3.connect(DB_FILE)
            self.cursor = self.conn.cursor()
        elif self.db_type == 'mysql':
            self.conn = mysql.connector.connect(
                host=os.getenv('DB_HOST'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME')
            )
            self.cursor = self.conn.cursor(buffered=True)

    def _execute_(self, query, data=None, commit=False, type=''):
        self._open_()
        self.cursor.execute(query, data)
        if commit:
            self.conn.commit()
        if type == 'fetchall':
            return self.cursor.fetchall()
        elif type == 'fetchone':
            return self.cursor.fetchone()
        elif type == 'lastrowid':
            return self.cursor.lastrowid

    def _open_(self):
        if self.conn.is_connected():
            return
        self._init_db()

    def _close_(self):
        self.conn.close()

    def __init__(self):
        self.db_type = os.getenv('DB_TYPE')
        self._init_db()
        self._create_tables()

    def insert_user(self, telegram_user_id, first_name, username):
        last_id = self._execute_(
            Queries[self.db_type]['insert_user'],
            (telegram_user_id, first_name, username),
            type='lastrowid')
        return last_id

    def insert_feedback(self, telegram_user_id, feedback):
        user = self.fetch_user(telegram_user_id)
        last_id = self._execute_(
            Queries[self.db_type]['insert_feedback'],
            (user[0], feedback, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            True,
            'lastrowid')
        return last_id

    def list_feedback(self):
        feedback = self._execute_(
            Queries[self.db_type]['get_all_feedback'],
            type='fetchall')
        return feedback

    def fetch_user(self, telegram_user_id):
        user = self._execute_(
                        Queries[self.db_type]['get_user'],
                        (telegram_user_id,),
                        type='fetchone')
        return user

    def insert_tracking(self, telegram_user_id, chat_id, url, type_of_compare):
        user = self.fetch_user(telegram_user_id)
        last_id = self._execute_(
                        Queries[self.db_type]['insert_tracking'],
                        (user[0], chat_id, url, type_of_compare),
                        True,
                        'lastrowid')
        return last_id

    def update_tracking(self, id, column, data):
        if column == 'old_image':
            self._execute_(
                Queries[self.db_type]['update_tracking_old_image'],
                (data, id),
                True)
        elif column == 'new_image':
            self._execute_(
                Queries[self.db_type]['update_tracking_new_image'],
                (data, id),
                True)
        elif column == 'last_run':
            self._execute_(
                Queries[self.db_type]['update_tracking_last_run'],
                (data, id),
                True)

    def fetch_tracking(self, id):
        track = self._execute_(Queries[self.db_type]['get_tracking_by_id'],
                               (id,),
                               type='fetchone')
        return track

    def delete_tracking(self, id):
        self._execute_(Queries[self.db_type]['delete_tracking'], (id,), True)
        self.conn.commit()

    def list_tracking(self, telegram_user_id):
        user = self.fetch_user(telegram_user_id)
        if user is None:
            return "You are not tracking anything"

        urls = self._execute_(Queries[self.db_type]['get_tracking'],
                              (user[0],),
                              type='fetchall')
        if len(urls) == 0:
            return "You are not tracking anything"
        return urls

    def list_all_tracking(self):
        all_list = self._execute_(Queries[self.db_type]['get_all_tracking'],
                                  type='fetchall')
        return all_list
