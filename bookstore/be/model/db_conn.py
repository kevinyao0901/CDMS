from be.model import store


class DBConn:
    def __init__(self):
        self.conn = store.get_db_conn()
        self.cur = self.conn.cursor()

    def user_id_exist(self, user_id):
        cursor = self.cur.execute(
            'SELECT user_id FROM "user" WHERE user_id = %s;', (user_id,)
        )
        row = self.cur.fetchone()
        if row is None:
            return False
        else:
            return True

    def book_id_exist(self, store_id, book_id):
        cursor = self.cur.execute(
            'SELECT book_id FROM store WHERE store_id = %s AND book_id = %s;',
            (store_id, book_id),
        )
        row = self.cur.fetchone()
        if row is None:
            return False
        else:
            return True

    def store_id_exist(self, store_id):
        cursor = self.cur.execute(
            'SELECT store_id FROM user_store WHERE store_id = %s;', (store_id,)
        )
        row = self.cur.fetchone()
        if row is None:
            return False
        else:
            return True
