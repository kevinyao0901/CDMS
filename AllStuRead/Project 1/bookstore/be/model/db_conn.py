from be.model import store


class DBConn:
    def __init__(self):
        self.conn = store.get_db_conn()

    def user_id_exist(self, user_id):
        cursor = self.conn['user'].find_one({"user_id": user_id})
        if cursor is None:
            return False
        else:
            return True

    def book_id_exist(self, store_id, book_id):
        cursor = self.conn['store'].find_one({'store_id': store_id, 'book_id': book_id})
        if cursor is None:
            return False
        else:
            return True

    def store_id_exist(self, store_id):
        cursor = self.conn['user_store'].find_one({'store_id': store_id})
        if cursor is None:
            return False
        else:
            return True
