import sqlite3
import os
import mysql.connector
from datetime import datetime

from .constants import DB_FILE


Queries = {
    'mysql': {
        'create_users': 'CREATE TABLE IF NOT EXISTS users \
                (id INT NOT NULL AUTO_INCREMENT, \
                telegram_user_id TEXT, first_name TEXT, username TEXT,\
                created_date TEXT, status_id INT,\
                PRIMARY KEY (id))',
        'create_tracking': 'CREATE TABLE IF NOT EXISTS tracking\
                (id INT NOT NULL AUTO_INCREMENT, \
                user_id INT, chat_id INT, url TEXT, type TEXT,\
                old_image TEXT, new_image TEXT, created_date TEXT,\
                m_interval INT, last_run TEXT, status_id INT,\
                PRIMARY KEY (id))',
        'create_feedback': 'CREATE TABLE IF NOT EXISTS feedback\
                (id INT NOT NULL AUTO_INCREMENT, \
                user_id INT, feedback TEXT, date TEXT,\
                PRIMARY KEY (id))',
        'create_compare_type': 'CREATE TABLE IF NOT EXISTS `compare_types` (\
                `id` INT NOT NULL AUTO_INCREMENT,\
                `name` VARCHAR(100),\
                `is_active` INT DEFAULT 1,\
                PRIMARY KEY (`id`));',
        'create_minutue_options': 'CREATE TABLE IF NOT EXISTS `minute_options`\
                (`id` INT NOT NULL AUTO_INCREMENT,\
                `name` VARCHAR(100),\
                `number_of_min` INT,\
                `display_order` INT DEFAULT 1,\
                `is_active` INT DEFAULT 1,\
                PRIMARY KEY (`id`));',
        'create_config': 'CREATE TABLE IF NOT EXISTS `configs` (\
                `id` INT NOT NULL AUTO_INCREMENT,\
                `env_key` VARCHAR(100),\
                `env_value` VARCHAR(1000),\
                PRIMARY KEY (`id`));',
        'insert_feedback': 'INSERT INTO feedback (user_id, feedback, date)'
        ' VALUES (%s, %s, %s)',
        'get_all_feedback': 'SELECT * FROM feedback',
        'insert_user': 'INSERT INTO users (telegram_user_id, first_name, '
        'username, created_date, status_id) VALUES (%s, %s, %s, %s, 1)',
        'insert_tracking': 'INSERT INTO tracking (user_id, chat_id, url, type,'
        ' created_date, m_interval, status_id) VALUES (%s, %s, %s, %s, %s, %s'
        ', 1)',
        'get_user': 'SELECT * FROM users WHERE telegram_user_id = %s',
        'get_all_users': 'SELECT * FROM users',
        'get_all_users_count': 'SELECT COUNT(*) FROM users',
        'get_user_by_id': 'SELECT * FROM users WHERE id = %s',
        'get_all_tracking': 'SELECT * FROM tracking where status_id = 1',
        'get_inactive_tracking': 'SELECT * FROM tracking where status_id = 0',
        'get_tracking': 'SELECT * FROM tracking WHERE user_id = %s '
        'and status_id = 1',
        'get_tracking_by_id': 'SELECT * FROM tracking WHERE id = %s '
        'and status_id = 1',
        'get_tracking_by_url': 'SELECT * FROM tracking WHERE url = %s',
        'update_tracking': 'UPDATE tracking SET old_image = %s, '
        'new_image = %s, last_run = %s WHERE id = %s',
        'update_tracking_old_image': 'UPDATE tracking SET '
        'old_image = %s WHERE id = %s',
        'update_tracking_new_image': 'UPDATE tracking SET '
        'new_image = %s WHERE id = %s',
        'update_tracking_last_run': 'UPDATE tracking SET '
        'last_run = %s WHERE id = %s',
        'update_tracking_interval': 'UPDATE tracking SET '
        'm_interval = %s WHERE id = %s',
        'soft_delete_tracking': 'UPDATE tracking SET '
        'status_id = 0 where id = %s',
        'delete_tracking': 'DELETE FROM tracking WHERE id = %s',
        'get_compare_types': 'SELECT * FROM compare_types'
        ' WHERE is_active = 1',
        'get_minute_options': 'SELECT * FROM minute_options'
        ' WHERE is_active = 1 order by display_order asc',
        'get_minute_option_by_min': 'SELECT * FROM minute_options'
        ' WHERE number_of_min = %s',
        'get_minute_option_by_name': 'SELECT * FROM minute_options'
        ' WHERE name = %s and is_active = 1',
        'get_configs': 'SELECT * FROM configs',
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
            (telegram_user_id, first_name, username,
             datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')),
            True,
            type='lastrowid')
        return last_id

    def insert_feedback(self, telegram_user_id, feedback):
        user = self.fetch_user(telegram_user_id)
        last_id = self._execute_(
            Queries[self.db_type]['insert_feedback'],
            (user[0], feedback,
             datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')),
            True,
            'lastrowid')
        return last_id

    def list_feedback(self):
        feedback = self._execute_(
            Queries[self.db_type]['get_all_feedback'],
            type='fetchall')
        return feedback

    def fetch_user_by_id(self, user_id):
        user = self._execute_(
                        Queries[self.db_type]['get_user_by_id'],
                        (user_id,),
                        type='fetchone')
        return user

    def fetch_user(self, telegram_user_id):
        user = self._execute_(
                        Queries[self.db_type]['get_user'],
                        (telegram_user_id,),
                        type='fetchone')
        return user

    def fetch_users(self):
        users = self._execute_(
                        Queries[self.db_type]['get_all_users'],
                        type='fetchall')
        return users

    def fetch_users_count(self):
        users = self._execute_(
                        Queries[self.db_type]['get_all_users_count'],
                        type='fetchone')
        return users[0]

    def fetch_compare_types(self):
        compare_types = self._execute_(
                        Queries[self.db_type]['get_compare_types'],
                        type='fetchall')
        return compare_types

    def insert_tracking(self, telegram_user_id, chat_id, url,
                        type_of_compare,
                        interval=60):
        user = self.fetch_user(telegram_user_id)
        last_id = self._execute_(
                        Queries[self.db_type]['insert_tracking'],
                        (user[0], chat_id, url, type_of_compare,
                         datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                         interval),
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
        elif column == 'interval':
            self._execute_(
                Queries[self.db_type]['update_tracking_interval'],
                (data, id),
                True)

    def fetch_tracking(self, id):
        track = self._execute_(Queries[self.db_type]['get_tracking_by_id'],
                               (id,),
                               type='fetchone')
        return track

    def delete_tracking(self, id):
        self._execute_(Queries[self.db_type]['soft_delete_tracking'], (id,),
                       True)
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

    def list_inactive_tracking(self):
        inactive_list = self._execute_(
            Queries[self.db_type]['get_inactive_tracking'],
            type='fetchall')
        return inactive_list

    def list_minute_options(self):
        minutes = self._execute_(
            Queries[self.db_type]['get_minute_options'],
            type='fetchall')
        return minutes

    def list_configs(self):
        configs = self._execute_(
            Queries[self.db_type]['get_configs'],
            type='fetchall')
        return configs

    def fetch_minute_option_by_name(self, name):
        minute = self._execute_(
            Queries[self.db_type]['get_minute_option_by_name'],
            (name,),
            type='fetchone')
        return minute

    def fetch_minute_option_by_min(self, id):
        minute = self._execute_(
            Queries[self.db_type]['get_minute_option_by_min'],
            (id,),
            type='fetchone')
        return minute
