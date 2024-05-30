import psycopg2
from be.model import error
from be.model import db_conn


class Seller(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)
        
    def add_book(
        self,
        user_id: str,
        store_id: str,
        book_id: str,
        book_json_str: str,
        stock_level: int,
    ):
        try:
            # Check if user and store exist
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            # Check if book already exists in the store
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            # Insert new book into the store
            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO store(store_id, book_id, book_info, stock_level) "
                        "VALUES (%s, %s, %s, %s)",
                        (store_id, book_id, book_json_str, stock_level),
                    )

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

    def add_stock_level(
        self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        try:
            # Check if user, store, and book exist
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            # Update stock level
            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute(
                        "UPDATE store SET stock_level = stock_level + %s "
                        "WHERE store_id = %s AND book_id = %s",
                        (add_stock_level, store_id, book_id),
                    )

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            # Check if user exists
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            # Check if store already exists
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)
            
            # Insert new store
            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO user_store(store_id, user_id) VALUES (%s, %s)",
                        (store_id, user_id),
                    )

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

    def ship_order(self, user_id: str, store_id: str, order_id: str) -> (int, str):
        try:
            # Check if user and store exist
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)

            # Query order status
            with self.conn:
                with self.conn.cursor() as cur:
                    cur.execute(
                        "SELECT status FROM order_history WHERE order_id = %s;",
                        (order_id,)
                    )
                    row = cur.fetchone()
                    if not row:
                        return error.error_invalid_order_id(order_id)

                    status = row[0]

                    # Check if order status is "paid"
                    if status != 'paid':
                        return error.error_not_paid(order_id)

                    # Update order history status to "shipped"
                    cur.execute(
                        "UPDATE order_history SET status = 'shipped' WHERE order_id = %s;",
                        (order_id,)
                    )
                    if cur.rowcount == 0:
                        return error.error_invalid_order_id(order_id)

            return 200, "ok"

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
