from be.model import store

class DBConn:
    def __init__(self):
        self.conn = store.get_db_conn()
        self.cur = self.conn.cursor()

    def user_id_exist(self, user_id):
        with self.conn.cursor() as cur:
            cur.execute(
                'SELECT EXISTS(SELECT 1 FROM "user" WHERE user_id = %s);', (user_id,)
            )
            return cur.fetchone()[0]

    def book_id_exist(self, store_id, book_id):
        with self.conn.cursor() as cur:
            cur.execute(
                'SELECT EXISTS(SELECT 1 FROM store WHERE store_id = %s AND book_id = %s);',
                (store_id, book_id),
            )
            return cur.fetchone()[0]

    def store_id_exist(self, store_id):
        with self.conn.cursor() as cur:
            cur.execute(
                'SELECT EXISTS(SELECT 1 FROM user_store WHERE store_id = %s);', (store_id,)
            )
            return cur.fetchone()[0]
