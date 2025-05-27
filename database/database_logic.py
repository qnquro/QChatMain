from psycopg2 import sql
import psycopg2 as ps
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, host, user, password, dbname):
        self.conn = ps.connect(
            host=host,
            user=user,
            password=password,
            dbname=dbname
        )
        self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    def get_main_themes(self):
        with self.conn.cursor() as cursor:
            cursor.execute(sql.SQL("SELECT id, title FROM themes WHERE parent_id is NULL"))
            return cursor.fetchall()

    def get_subthemes(self, parent_id):
        with self.conn.cursor() as cursor:
            cursor.execute(sql.SQL("SELECT id, title FROM themes WHERE parent_id = %s"), (parent_id,))
            return cursor.fetchall()

    def get_discussions(self, theme_id):
        with self.conn.cursor() as cursor:
            cursor.execute(sql.SQL("""
                SELECT id, author, content 
                FROM discussions 
                WHERE theme_id = %s AND is_root = TRUE
                ORDER BY created_at DESC
            """), (theme_id,))
            return cursor.fetchall()

    def get_discussion(self, discussion_id):
        with self.conn.cursor() as cursor:
            print(discussion_id)
            cursor.execute(sql.SQL("""
            SELECT id, author, content, theme_id
            FROM discussions
            WHERE id = %s AND is_root=TRUE
            """), (discussion_id,))
            row = cursor.fetchone()
            if row:
                return {'id': row[0], 'author': row[1], 'content': row[2], 'theme_id': row[3]}
            return None

    def get_replies(self, discussion_id):
        with self.conn.cursor() as cursor:
            cursor.execute(sql.SQL("""
            SELECT author, content, content_type, media_id, user_id 
            FROM discussions
            WHERE parent_discussion_id = %s
            ORDER BY created_at ASC
            """), (discussion_id,))
            return [{'author': row[0], 'content': row[1], 'content_type': row[2], 'media_id': row[3], 'user_id':row[4] } for row in cursor.fetchall()]

    def add_reply(self, parent_id, author, content, content_type, media_id, user_id = None):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql.SQL("""
                INSERT INTO discussions(theme_id, parent_discussion_id, author, content, content_type, media_id, is_root, user_id)
                SELECT theme_id, %s, %s, %s, %s, %s, FALSE, %s
                FROM discussions
                WHERE id = %s
                """), (parent_id, author, content, content_type, media_id, user_id, parent_id))
        except ps.Error as e:
            logger.error(f"Ошибка при добавлении ответа {e}")
            raise RuntimeError("Reply add is failed") from e

    def add_discussion(self, theme_id,author, content):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql.SQL("""
                INSERT INTO discussions(theme_id, author, content, is_root)
                VALUES (%s, %s, %s, TRUE)
                """), (theme_id, author, content))
        except ps.Error as e:
            logger.error(f"Ошибка при добавлении дискуссии {e}")
            raise RuntimeError("Discussion add is failed") from e
