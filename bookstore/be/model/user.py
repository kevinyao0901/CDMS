import jwt
import time
import logging
import sqlite3 as sqlite
from be.model import error
from be.model import db_conn
import psycopg2

class User(db_conn.DBConn):
    token_lifetime: int = 3600  # 3600 second

    def __init__(self):
        db_conn.DBConn.__init__(self)

    def __check_token(self, user_id, db_token, token) -> bool:
        try:
            if db_token != token:
                return False
            jwt_text = self.jwt_decode(encoded_token=token, user_id=user_id)
            ts = jwt_text["timestamp"]
            if ts is not None:
                now = time.time()
                if self.token_lifetime > now - ts >= 0:
                    return True
        except jwt.exceptions.InvalidSignatureError as e:
            logging.error(str(e))
            return False

    def register(self, user_id: str, password: str):
        if self.user_id_exist(user_id):
            return error.error_exist_user_id(user_id)
        try:
            terminal = "terminal_{}".format(str(time.time()))
            self.cur.execute(
                'INSERT INTO "user"(user_id, password, balance, token, terminal) '
                'VALUES (%s, %s, %s, %s, %s) RETURNING token;',
                (user_id, password, 0, self.jwt_encode(user_id, terminal), terminal),
            )
            self.conn.commit()
        except psycopg2.Error as e:
            return 528, str(e)
        finally:
            if self.cur:
                self.cur.close()
            if self.conn:
                self.conn.close()
        return 200, "ok"

    def check_token(self, user_id: str, token: str) -> (int, str):
        self.cur.execute('SELECT token from "user" where user_id=%s', (user_id,))
        row = self.cur.fetchone()
        if row is None:
            return error.error_authorization_fail()
        db_token = row[0]
        if not self.__check_token(user_id, db_token, token):
            return error.error_authorization_fail()
        return 200, "ok"

    def check_password(self, user_id: str, password: str) -> (int, str):
        self.cur.execute('SELECT password from "user" where user_id=%s', (user_id,))
        row = self.cur.fetchone()
        if (row is None) or (password != row[0]):
            return error.error_authorization_fail()

        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        token = ""
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""

            token = self.jwt_encode(user_id, terminal)
            self.cur.execute(
                'UPDATE "user" SET (token, terminal) = (%s, %s) WHERE user_id = %s RETURNING token;',
                (token, terminal, user_id),
            )
            self.conn.commit()
        except psycopg2.Error as e:
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            return 530, "{}".format(str(e)), ""
        finally:
            self.cur.close()
            self.conn.close()
        return 200, "ok", token

    def logout(self, user_id: str, token: str) -> bool:
        try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            dummy_token = self.jwt_encode(user_id, terminal)

            self.cur.execute(
                'UPDATE "user" SET (token, terminal) = (%s, %s) WHERE user_id = %s RETURNING token;',
                (dummy_token, terminal, user_id),
            )
            if self.cur.rowcount == 0:
                return error.error_authorization_fail()

            self.conn.commit()
        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        finally:
            self.cur.close()
            self.conn.close()
        return 200, "ok"

    def unregister(self, user_id: str, password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message

            self.cur.execute('DELETE from "user" where user_id=%s', (user_id,))
            if self.cur.rowcount == 1:
                self.conn.commit()
            else:
                return error.error_authorization_fail()
        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        finally:
            self.cur.close()
            self.conn.close()
        return 200, "ok"

    def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> bool:
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            token = self.jwt_encode(user_id, terminal)
            self.cur.execute(
                'UPDATE "user" set (password, token, terminal) = (%s, %s, %s) where user_id = %s RETURNING token;',
                (new_password, token, terminal, user_id),
            )
            if self.cur.rowcount == 0:
                return error.error_authorization_fail()

            self.conn.commit()
        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        finally:
            self.cur.close()
            self.conn.close()
        return 200, "ok"

    def search_book(self, title='', content='', tag='', store_id=''):
        try:
            # 建立数据库连接
            book_db = "D:/db_project2/wen/project 2/bookstore/fe/data/book.db"
            cursor = self.conn.cursor()

            query_conditions = []
            query_parameters = []

            if title:
                query_conditions.append("title LIKE ?")
                query_parameters.append(f"%{title}%")

            if content:
                query_conditions.append("content LIKE ?")
                query_parameters.append(f"%{content}%")

            if tag:
                query_conditions.append("tags LIKE ?")
                query_parameters.append(f"%{tag}%")

            if store_id:
                # 查询 store 表，获取指定 store_id 下的所有 book_id
                self.cur.execute("SELECT book_id FROM store WHERE store_id = %s", (store_id,))
                book_ids = [row[0] for row in self.cur.fetchall()]

                if not book_ids:
                    return error.error_non_exist_store_id(store_id)

                # 构建 IN 子句，使用多个占位符
                in_clause = ",".join("?" for _ in book_ids)
                query_conditions.append(f"id IN ({in_clause})")
                query_parameters.extend(book_ids)

            if not query_conditions:
                return 200, "ok"

            # 构建查询字符串
            query_string = "SELECT * FROM book WHERE " + " AND ".join(query_conditions)
            conn = sqlite.connect(book_db)
            cursor = conn.execute(query_string, query_parameters)

            results = cursor.fetchall()

        except psycopg2.Error as e:
            return 528, str(e)
        except sqlite.Error as e:
            return 528, str(e)
        except BaseException as e:
            return 530, str(e)
        finally:
            self.cur.close()
            self.conn.close()

        if not results:
            return 529, "No matching books found."
        else:
            return 200, "ok"
        
    def jwt_encode(self, user_id: str, terminal: str) -> str:
        try:
            payload = {"user_id": user_id, "terminal": terminal, "timestamp": time.time()}
            encoded_token = jwt.encode(payload, key=user_id, algorithm="HS256").encode("utf-8")
            return encoded_token.decode("utf-8")
        except BaseException:
            return None
        
    def jwt_decode(self, encoded_token, user_id: str) -> str:
        try:
            decoded = jwt.decode(encoded_token, key=user_id, algorithms="HS256")
            return decoded
        except BaseException:
            return None        
